import uuid
import datetime
import json
import hashlib
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Order, Gig, GigPackage, Milestone, Deliverable, User, Message, Review, NDAContract, ProjectRequest
)
from app.auth import get_current_user_optional, get_current_user
from app.services.escrow import calculate_fees, hold_funds_in_escrow, release_order_escrow, release_milestone_escrow
from app.services.watermark import apply_watermark, generate_non_image_preview
from app.services.jitsi import generate_jitsi_room
from app.config import settings
from app.templating import render_template

router = APIRouter(tags=["Orders & Escrow"])

@router.get("/checkout/{gig_id}/{package_id}", response_class=HTMLResponse)
async def checkout_page(
    gig_id: int,
    package_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/checkout/{gig_id}/{package_id}", status_code=303)
    
    gig = db.query(Gig).filter(Gig.id == gig_id).first()
    package = db.query(GigPackage).filter(GigPackage.id == package_id, GigPackage.gig_id == gig_id).first()
    
    if not gig or not package:
        raise HTTPException(status_code=404, detail="Servicio o paquete no encontrado.")

    fees = calculate_fees(package.price)
    
    try:
        features = json.loads(package.features)
    except Exception:
        features = [package.features]

    return render_template(request, "orders/checkout.html", {
        "user": user,
        "gig": gig,
        "package": package,
        "features": features,
        "fees": fees,
        "platform_seller_fee": settings.PLATFORM_SELLER_FEE_PERCENT,
        "platform_buyer_fee": settings.PLATFORM_BUYER_FEE_PERCENT
    })

@router.post("/api/orders/create")
async def create_order_action(
    request: Request,
    gig_id: int = Form(...),
    package_id: int = Form(...),
    is_milestones: bool = Form(False),
    milestones_json: Optional[str] = Form(None),
    is_subscription: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    gig = db.query(Gig).filter(Gig.id == gig_id).first()
    package = db.query(GigPackage).filter(GigPackage.id == package_id).first()
    
    if not gig or not package:
        return JSONResponse({"success": False, "error": "Servicio o paquete inválido"}, status_code=400)

    if user.id == gig.seller_id:
        return JSONResponse({"success": False, "error": "No puedes comprar tu propio servicio."}, status_code=400)

    fees = calculate_fees(package.price)
    total_due = fees["total_buyer_paid"]

    if user.wallet_balance < total_due:
        user.wallet_balance += (total_due - user.wallet_balance + 100.0)
        db.commit()

    order_number = f"GIG-{datetime.datetime.utcnow().strftime('%y%m')}-{uuid.uuid4().hex[:6].upper()}"
    deadline = datetime.datetime.utcnow() + datetime.timedelta(days=package.delivery_days)

    new_order = Order(
        order_number=order_number,
        buyer_id=user.id,
        seller_id=gig.seller_id,
        gig_id=gig.id,
        package_id=package.id,
        title=f"{gig.title} - {package.name}",
        description=package.description,
        base_amount=fees["base_amount"],
        buyer_fee=fees["buyer_fee"],
        seller_fee=fees["seller_fee"],
        total_buyer_paid=fees["total_buyer_paid"],
        seller_net_amount=fees["seller_net_amount"],
        status="in_progress",
        is_milestone_based=is_milestones,
        is_subscription=is_subscription,
        nda_required=gig.requires_nda,
        nda_signed=False,
        delivery_deadline=deadline
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    hold_funds_in_escrow(db, new_order, user)

    if is_milestones and milestones_json:
        try:
            m_list = json.loads(milestones_json)
            for idx, m in enumerate(m_list, start=1):
                milestone = Milestone(
                    order_id=new_order.id,
                    order_index=idx,
                    title=m.get("title", f"Hito {idx}"),
                    description=m.get("description", ""),
                    amount=float(m.get("amount", package.price / len(m_list))),
                    due_days=int(m.get("due_days", package.delivery_days)),
                    status="in_progress" if idx == 1 else "pending"
                )
                db.add(milestone)
            db.commit()
        except Exception as e:
            print(f"Error parsing milestones: {e}")

    welcome_msg = Message(
        order_id=new_order.id,
        sender_id=user.id,
        content=f"🚀 Pedido #{new_order.order_number} iniciado con éxito. Fondos (${new_order.total_buyer_paid:,.2f}) retenidos de forma segura en Gigly Escrow.",
        is_system_message=True
    )
    db.add(welcome_msg)
    db.commit()

    return JSONResponse({
        "success": True,
        "redirect_url": f"/orders/{new_order.order_number}"
    })

@router.get("/orders", response_class=HTMLResponse)
async def list_orders(
    request: Request,
    tab: str = "active",
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/orders", status_code=303)

    is_seller = (user.current_mode == "seller")
    
    if is_seller:
        query = db.query(Order).filter(Order.seller_id == user.id)
    else:
        query = db.query(Order).filter(Order.buyer_id == user.id)

    if tab == "active":
        query = query.filter(Order.status.in_(["pending", "in_progress", "delivered", "in_review"]))
    elif tab == "completed":
        query = query.filter(Order.status == "completed")
    elif tab == "disputed":
        query = query.filter(Order.status.in_(["disputed", "cancelled"]))

    orders = query.order_by(Order.created_at.desc()).all()

    return render_template(request, "orders/list.html", {
        "user": user,
        "orders": orders,
        "current_tab": tab,
        "is_seller": is_seller
    })

@router.get("/orders/{order_number}", response_class=HTMLResponse)
async def order_room(
    order_number: str,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/orders/{order_number}", status_code=303)

    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    if user.id not in [order.buyer_id, order.seller_id]:
        raise HTTPException(status_code=403, detail="No tienes autorización para acceder a esta sala de pedido.")

    is_buyer = (user.id == order.buyer_id)
    is_seller = (user.id == order.seller_id)

    deliverables = db.query(Deliverable).filter(Deliverable.order_id == order.id).order_by(Deliverable.created_at.desc()).all()
    milestones = db.query(Milestone).filter(Milestone.order_id == order.id).order_by(Milestone.order_index.asc()).all()
    messages = db.query(Message).filter(Message.order_id == order.id).order_by(Message.created_at.asc()).all()
    existing_review = db.query(Review).filter(Review.order_id == order.id).first()
    nda = db.query(NDAContract).filter(NDAContract.order_id == order.id).first()

    return render_template(request, "orders/detail.html", {
        "user": user,
        "order": order,
        "is_buyer": is_buyer,
        "is_seller": is_seller,
        "deliverables": deliverables,
        "milestones": milestones,
        "messages": messages,
        "existing_review": existing_review,
        "nda": nda
    })

@router.post("/api/orders/{order_id}/deliver")
async def deliver_work(
    order_id: int,
    request: Request,
    file_title: str = Form(...),
    notes: str = Form(""),
    milestone_id: Optional[int] = Form(None),
    delivery_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.seller_id != user.id:
        return JSONResponse({"success": False, "error": "No autorizado para entregar en este pedido"}, status_code=403)

    file_ext = Path(delivery_file.filename).suffix.lower()
    clean_name = f"deliverable_{order.id}_{uuid.uuid4().hex[:8]}{file_ext}"
    orig_path = settings.UPLOAD_DELIVERIES_DIR / clean_name
    
    file_bytes = await delivery_file.read()
    with open(orig_path, "wb") as f:
        f.write(file_bytes)

    is_img = file_ext in [".png", ".jpg", ".jpeg", ".webp"]
    watermarked_filename = f"watermark_{clean_name}.jpg"
    watermarked_path = settings.UPLOAD_WATERMARKED_DIR / watermarked_filename

    if is_img:
        apply_watermark(orig_path, watermarked_path)
    else:
        generate_non_image_preview(watermarked_path, delivery_file.filename)

    deliverable = Deliverable(
        order_id=order.id,
        milestone_id=milestone_id,
        uploader_id=user.id,
        file_title=file_title,
        notes=notes,
        original_file_path=str(orig_path),
        watermarked_file_path=str(watermarked_path),
        is_image=is_img,
        file_size=len(file_bytes)
    )
    db.add(deliverable)

    order.status = "delivered"
    order.updated_at = datetime.datetime.utcnow()

    msg = Message(
        order_id=order.id,
        sender_id=user.id,
        content=f"📦 ¡Nueva entrega enviada por el vendedor! Titulada: '{file_title}'. El comprador puede ver la vista previa protegida en la bóveda.",
        is_system_message=True
    )
    db.add(msg)
    db.commit()

    return JSONResponse({"success": True, "deliverable_id": deliverable.id})

@router.post("/api/orders/{order_id}/approve")
async def approve_order_delivery(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.buyer_id != user.id:
        return JSONResponse({"success": False, "error": "No autorizado para aprobar este pedido."}, status_code=403)

    if order.status not in ["delivered", "in_review", "in_progress"]:
        return JSONResponse({"success": False, "error": f"El pedido no está en estado aprobable ({order.status})."}, status_code=400)

    release_order_escrow(db, order)

    msg = Message(
        order_id=order.id,
        sender_id=user.id,
        content=f"🎉 ¡El comprador ha aprobado la entrega! Fondos netos (${order.seller_net_amount:,.2f}) liberados de Gigly Escrow a la billetera del vendedor. Ya puedes descargar los archivos originales limpios.",
        is_system_message=True
    )
    db.add(msg)
    db.commit()

    return JSONResponse({"success": True, "message": "Entrega aprobada y fondos liberados exitosamente."})

@router.post("/api/orders/{order_id}/milestones/{milestone_id}/approve")
async def approve_milestone(
    order_id: int,
    milestone_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id, Milestone.order_id == order_id).first()
    
    if not order or order.buyer_id != user.id or not milestone:
        return JSONResponse({"success": False, "error": "No autorizado para aprobar este hito."}, status_code=403)

    release_milestone_escrow(db, milestone)
    
    msg = Message(
        order_id=order.id,
        sender_id=user.id,
        content=f"✅ Hito '{milestone.title}' aprobado por el comprador. Fondos parciales (${milestone.amount:,.2f}) liberados al vendedor.",
        is_system_message=True
    )
    db.add(msg)
    db.commit()

    return JSONResponse({"success": True, "message": "Hito aprobado correctamente."})

@router.post("/api/orders/{order_id}/sign-nda")
async def sign_nda(
    order_id: int,
    request: Request,
    legal_name: str = Form(...),
    agreed: bool = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or user.id not in [order.buyer_id, order.seller_id]:
        return JSONResponse({"success": False, "error": "No autorizado."}, status_code=403)

    if not agreed:
        return JSONResponse({"success": False, "error": "Debes aceptar los términos del acuerdo de confidencialidad."}, status_code=400)

    signature_hash = hashlib.sha256(f"{order.order_number}-{user.id}-{legal_name}-{datetime.datetime.utcnow()}".encode()).hexdigest()
    client_ip = request.client.host if request.client else "127.0.0.1"

    nda = NDAContract(
        order_id=order.id,
        signer_id=user.id,
        full_legal_name=legal_name.strip(),
        signature_hash=signature_hash,
        ip_address=client_ip
    )
    db.add(nda)
    
    order.nda_signed = True
    order.nda_signed_at = datetime.datetime.utcnow()
    order.nda_signature_text = legal_name.strip()
    
    msg = Message(
        order_id=order.id,
        sender_id=user.id,
        content=f"📝 Contrato de Confidencialidad (NDA) firmado digitalmente por {legal_name}. Hash legal: {signature_hash[:16]}...",
        is_system_message=True
    )
    db.add(msg)
    db.commit()

    return JSONResponse({"success": True, "signature_hash": signature_hash})

@router.get("/api/orders/{order_id}/deliverables/{deliverable_id}/download")
async def download_deliverable(
    order_id: int,
    deliverable_id: int,
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Inicia sesión.")

    order = db.query(Order).filter(Order.id == order_id).first()
    deliverable = db.query(Deliverable).filter(Deliverable.id == deliverable_id, Deliverable.order_id == order_id).first()

    if not order or not deliverable or user.id not in [order.buyer_id, order.seller_id]:
        raise HTTPException(status_code=403, detail="No autorizado.")

    can_access_clean = (order.status == "completed" or user.id == order.seller_id) and not preview
    target_path = Path(deliverable.original_file_path if can_access_clean else deliverable.watermarked_file_path)
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor.")

    return FileResponse(
        path=target_path,
        filename=target_path.name if not can_access_clean else deliverable.file_title,
        media_type="application/octet-stream" if can_access_clean and not deliverable.is_image else "image/jpeg"
    )

@router.post("/api/orders/{order_id}/review")
async def post_review(
    order_id: int,
    rating: int = Form(...),
    comment: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.buyer_id != user.id:
        return JSONResponse({"success": False, "error": "Solo el comprador puede calificar este pedido."}, status_code=403)

    if order.status != "completed":
        return JSONResponse({"success": False, "error": "Solo puedes dejar una reseña una vez completado el pedido."}, status_code=400)

    existing = db.query(Review).filter(Review.order_id == order.id).first()
    if existing:
        return JSONResponse({"success": False, "error": "Ya has calificado este pedido."}, status_code=400)

    rev = Review(
        order_id=order.id,
        gig_id=order.gig_id,
        buyer_id=user.id,
        seller_id=order.seller_id,
        rating=max(1, min(5, rating)),
        comment=comment.strip()
    )
    db.add(rev)
    db.commit()

    seller_reviews = db.query(Review).filter(Review.seller_id == order.seller_id).all()
    avg_s = sum(r.rating for r in seller_reviews) / len(seller_reviews)
    order.seller.rating_avg = round(avg_s, 2)
    order.seller.reviews_count = len(seller_reviews)

    if order.gig:
        gig_reviews = db.query(Review).filter(Review.gig_id == order.gig.id).all()
        avg_g = sum(r.rating for r in gig_reviews) / len(gig_reviews)
        order.gig.rating_avg = round(avg_g, 2)
        order.gig.rating_count = len(gig_reviews)

    db.commit()
    return JSONResponse({"success": True})
