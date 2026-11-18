import json
import re
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database import get_db
from app.models import Gig, GigPackage, User, Review
from app.auth import get_current_user_optional, get_current_user
from app.config import settings
from app.templating import render_template

router = APIRouter(tags=["Gigs"])

CATEGORIES = [
    "Programación & Tech",
    "Diseño & Creatividad",
    "Marketing Digital",
    "Redacción & Traducción",
    "Video & Animación",
    "Audio & Música",
    "Negocios & Finanzas"
]

def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[-\s]+", "-", text)

@router.get("/gigs", response_class=HTMLResponse)
async def list_gigs(
    request: Request,
    q: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    delivery_days: Optional[int] = None,
    min_rating: Optional[float] = None,
    requires_nda: Optional[bool] = None,
    allows_retainer: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    query = db.query(Gig).filter(Gig.is_active == True)

    if q:
        search_filter = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Gig.title.ilike(search_filter),
                Gig.description.ilike(search_filter),
                Gig.tags.ilike(search_filter)
            )
        )

    if category and category != "all":
        query = query.filter(Gig.category == category)

    if min_rating:
        query = query.filter(Gig.rating_avg >= min_rating)

    if requires_nda is True:
        query = query.filter(Gig.requires_nda == True)

    if allows_retainer is True:
        query = query.filter(Gig.allows_retainer == True)

    gigs = query.all()

    # Filter by price or delivery days based on packages
    filtered_gigs = []
    for gig in gigs:
        basic_pkg = next((p for p in gig.packages if p.tier == "basic"), None)
        if not basic_pkg and gig.packages:
            basic_pkg = gig.packages[0]
            
        if basic_pkg:
            price = basic_pkg.price
            days = basic_pkg.delivery_days
            
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            if delivery_days is not None and days > delivery_days:
                continue
                
        filtered_gigs.append(gig)

    return render_template(request, "gigs/list.html", {
        "user": user,
        "gigs": filtered_gigs,
        "categories": CATEGORIES,
        "selected_category": category,
        "search_query": q or "",
        "min_price": min_price,
        "max_price": max_price,
        "delivery_days": delivery_days,
        "min_rating": min_rating,
        "requires_nda": requires_nda,
        "allows_retainer": allows_retainer
    })

@router.get("/gigs/new", response_class=HTMLResponse)
async def create_gig_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/gigs/new", status_code=303)
    
    return render_template(request, "gigs/create.html", {
        "user": user,
        "categories": CATEGORIES,
        "error": None
    })

@router.post("/gigs/new")
async def create_gig_action(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    sub_category: str = Form("General"),
    description: str = Form(...),
    tags: str = Form(""),
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    requires_nda: bool = Form(False),
    allows_retainer: bool = Form(False),
    retainer_monthly_price: Optional[float] = Form(None),
    
    # Basic package
    basic_name: str = Form("Plan Básico"),
    basic_desc: str = Form(...),
    basic_days: int = Form(3),
    basic_revisions: int = Form(1),
    basic_price: float = Form(...),
    basic_features: str = Form(""),
    
    # Standard package
    standard_name: str = Form("Plan Estándar"),
    standard_desc: str = Form(...),
    standard_days: int = Form(5),
    standard_revisions: int = Form(3),
    standard_price: float = Form(...),
    standard_features: str = Form(""),
    
    # Premium package
    premium_name: str = Form("Plan Premium Pro"),
    premium_desc: str = Form(...),
    premium_days: int = Form(7),
    premium_revisions: int = Form(-1),
    premium_price: float = Form(...),
    premium_features: str = Form(""),
    
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    final_image_url = image_url or "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800&auto=format&fit=crop&q=80"
    
    if image_file and image_file.filename:
        filename = f"gig_{user.id}_{image_file.filename}"
        filepath = settings.UPLOAD_GIGS_DIR / filename
        with open(filepath, "wb") as f:
            f.write(await image_file.read())
        final_image_url = f"/uploads/gigs/{filename}"

    base_slug = slugify(title)
    existing_slug = db.query(Gig).filter(Gig.slug == base_slug).first()
    if existing_slug:
        base_slug = f"{base_slug}-{user.id}-{int(request.client.port if request.client else 100)}"

    new_gig = Gig(
        seller_id=user.id,
        title=title,
        slug=base_slug,
        category=category,
        sub_category=sub_category,
        description=description,
        tags=tags,
        image_url=final_image_url,
        requires_nda=requires_nda,
        allows_retainer=allows_retainer,
        retainer_monthly_price=retainer_monthly_price if allows_retainer else None
    )
    db.add(new_gig)
    db.commit()
    db.refresh(new_gig)

    def parse_features(text: str):
        lines = [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]
        return json.dumps(lines if lines else ["Entrega garantizada", "Soporte Gigly"])

    packages = [
        GigPackage(
            gig_id=new_gig.id,
            tier="basic",
            name=basic_name,
            description=basic_desc,
            delivery_days=basic_days,
            revisions=basic_revisions,
            price=basic_price,
            features=parse_features(basic_features)
        ),
        GigPackage(
            gig_id=new_gig.id,
            tier="standard",
            name=standard_name,
            description=standard_desc,
            delivery_days=standard_days,
            revisions=standard_revisions,
            price=standard_price,
            features=parse_features(standard_features)
        ),
        GigPackage(
            gig_id=new_gig.id,
            tier="premium",
            name=premium_name,
            description=premium_desc,
            delivery_days=premium_days,
            revisions=premium_revisions,
            price=premium_price,
            features=parse_features(premium_features)
        )
    ]
    db.add_all(packages)
    db.commit()

    return RedirectResponse(url=f"/gigs/{new_gig.slug}", status_code=303)

@router.get("/gigs/{slug}", response_class=HTMLResponse)
async def gig_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    gig = db.query(Gig).filter(Gig.slug == slug).first()
    if not gig:
        raise HTTPException(status_code=404, detail="El servicio no existe o ha sido retirado.")

    packages_by_tier = {pkg.tier: pkg for pkg in gig.packages}
    reviews = db.query(Review).filter(Review.gig_id == gig.id).order_by(Review.created_at.desc()).all()

    parsed_packages = {}
    for tier, pkg in packages_by_tier.items():
        try:
            feats = json.loads(pkg.features)
        except Exception:
            feats = [pkg.features]
        parsed_packages[tier] = {
            "pkg": pkg,
            "features": feats
        }

    return render_template(request, "gigs/detail.html", {
        "user": user,
        "gig": gig,
        "packages": parsed_packages,
        "reviews": reviews,
        "platform_seller_fee": settings.PLATFORM_SELLER_FEE_PERCENT,
        "platform_buyer_fee": settings.PLATFORM_BUYER_FEE_PERCENT
    })
