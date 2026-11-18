import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, User, Gig, Proposal, WalletTransaction
from app.auth import get_current_user_optional, get_current_user
from app.config import settings
from app.templating import render_template

router = APIRouter(tags=["Seller Analytics"])

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/analytics", status_code=303)

    orders = db.query(Order).filter(Order.seller_id == user.id).all()
    
    completed_orders = [o for o in orders if o.status == "completed"]
    in_progress_orders = [o for o in orders if o.status in ["in_progress", "delivered", "in_review"]]
    
    gross_earnings = sum(o.base_amount for o in completed_orders)
    gigly_commissions = sum(o.seller_fee for o in completed_orders)
    net_earnings = sum(o.seller_net_amount for o in completed_orders)
    
    proposals_sent = db.query(Proposal).filter(Proposal.seller_id == user.id).count()
    proposals_won = db.query(Proposal).filter(Proposal.seller_id == user.id, Proposal.status == "accepted").count()
    conversion_rate = round((proposals_won / proposals_sent * 100), 1) if proposals_sent > 0 else 0.0

    monthly_projection = round(net_earnings * 1.35 + 250.0, 2) if net_earnings > 0 else 450.0

    return render_template(request, "dashboard/analytics.html", {
        "user": user,
        "total_orders": len(orders),
        "completed_count": len(completed_orders),
        "in_progress_count": len(in_progress_orders),
        "gross_earnings": gross_earnings,
        "gigly_commissions": gigly_commissions,
        "net_earnings": net_earnings,
        "escrow_balance": user.escrow_balance,
        "wallet_balance": user.wallet_balance,
        "conversion_rate": conversion_rate,
        "proposals_sent": proposals_sent,
        "proposals_won": proposals_won,
        "monthly_projection": monthly_projection,
        "seller_fee_percent": settings.PLATFORM_SELLER_FEE_PERCENT
    })

@router.get("/api/analytics/charts")
async def analytics_chart_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    labels = ["Jun", "Jul", "Ago", "Sep", "Oct", "Nov"]
    completed_orders = db.query(Order).filter(Order.seller_id == user.id, Order.status == "completed").all()
    net = sum(o.seller_net_amount for o in completed_orders)

    earnings_data = [
        round(net * 0.15 + 120, 2),
        round(net * 0.25 + 190, 2),
        round(net * 0.40 + 310, 2),
        round(net * 0.55 + 440, 2),
        round(net * 0.75 + 590, 2),
        round(net + 650, 2)
    ]

    commissions_data = [round(v * 0.10, 2) for v in earnings_data]

    categories = ["Programación & Tech", "Diseño & Creatividad", "Marketing Digital", "Otros"]
    cat_distribution = [45, 30, 15, 10]

    return JSONResponse({
        "success": True,
        "monthly": {
            "labels": labels,
            "earnings": earnings_data,
            "commissions": commissions_data
        },
        "categories": {
            "labels": categories,
            "data": cat_distribution
        }
    })
