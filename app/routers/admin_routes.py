import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Gig, Order, ProjectRequest, WalletTransaction
from app.auth import get_current_user_optional, get_current_admin
from app.services.escrow import release_order_escrow, refund_order_escrow
from app.templating import render_template

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/admin", status_code=303)
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido. Esta área es exclusiva para Administradores de Gigly."
        )

    # Global Platform Metrics
    total_users = db.query(User).count()
    total_gigs = db.query(Gig).count()
    orders = db.query(Order).all()
    
    completed_orders = [o for o in orders if o.status == "completed"]
    in_progress_orders = [o for o in orders if o.status in ["in_progress", "delivered", "in_review"]]
    disputed_orders = [o for o in orders if o.status in ["disputed", "in_review", "delivered"]]

    # Platform gross merchandise volume (GMV)
    gmv_volume = sum(o.total_buyer_paid for o in completed_orders)
    
    # Net Platform Revenues (10% from sellers + 3% from buyers)
    platform_revenue = sum(o.seller_fee + o.buyer_fee for o in completed_orders)

    # Active money in Escrow
    active_escrow = sum(o.base_amount for o in in_progress_orders)

    # Recent users and gigs
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(8).all()
    recent_gigs = db.query(Gig).order_by(Gig.created_at.desc()).limit(8).all()

    return render_template(request, "admin/dashboard.html", {
        "user": user,
        "total_users": total_users,
        "total_gigs": total_gigs,
        "total_orders": len(orders),
        "completed_count": len(completed_orders),
        "gmv_volume": gmv_volume,
        "platform_revenue": platform_revenue,
        "active_escrow": active_escrow,
        "disputed_orders": disputed_orders,
        "recent_users": recent_users,
        "recent_gigs": recent_gigs
    })

@router.post("/api/orders/{order_id}/resolve")
async def resolve_order_dispute(
    order_id: int,
    action: str = Form(...),  # "release_seller" or "refund_buyer"
    reason: str = Form(""),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return JSONResponse({"success": False, "error": "Pedido no encontrado"}, status_code=404)

    if action == "release_seller":
        release_order_escrow(db, order)
        return JSONResponse({"success": True, "message": "Fondos liberados con éxito al vendedor."})
    elif action == "refund_buyer":
        refund_order_escrow(db, order, reason)
        return JSONResponse({"success": True, "message": "Fondos reembolsados con éxito al comprador."})

    return JSONResponse({"success": False, "error": "Acción no reconocida"}, status_code=400)

@router.post("/api/gigs/{gig_id}/toggle")
async def toggle_gig_status(
    gig_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    gig = db.query(Gig).filter(Gig.id == gig_id).first()
    if not gig:
        return JSONResponse({"success": False, "error": "Gig no encontrado"}, status_code=404)

    gig.is_active = not gig.is_active
    db.commit()
    return JSONResponse({"success": True, "is_active": gig.is_active})

@router.post("/api/users/{user_id}/verify")
async def toggle_user_verification(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        return JSONResponse({"success": False, "error": "Usuario no encontrado"}, status_code=404)

    target_user.is_verified = not target_user.is_verified
    db.commit()
    return JSONResponse({"success": True, "is_verified": target_user.is_verified})
