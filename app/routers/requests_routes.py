import uuid
import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ProjectRequest, Proposal, Order, User, Message
from app.auth import get_current_user_optional, get_current_user
from app.services.escrow import calculate_fees, hold_funds_in_escrow
from app.routers.gigs_routes import CATEGORIES
from app.templating import render_template

router = APIRouter(tags=["Reverse Job Board"])

@router.get("/requests", response_class=HTMLResponse)
async def list_requests(
    request: Request,
    category: Optional[str] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    query = db.query(ProjectRequest).filter(ProjectRequest.status == "open")

    if category and category != "all":
        query = query.filter(ProjectRequest.category == category)
    if min_budget is not None:
        query = query.filter(ProjectRequest.budget >= min_budget)
    if max_budget is not None:
        query = query.filter(ProjectRequest.budget <= max_budget)

    requests_list = query.order_by(ProjectRequest.created_at.desc()).all()

    return render_template(request, "requests/list.html", {
        "user": user,
        "requests": requests_list,
        "categories": CATEGORIES,
        "selected_category": category,
        "min_budget": min_budget,
        "max_budget": max_budget
    })

@router.get("/requests/new", response_class=HTMLResponse)
async def create_request_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/requests/new", status_code=303)

    return render_template(request, "requests/create.html", {
        "user": user,
        "categories": CATEGORIES
    })

@router.post("/requests/new")
async def create_request_action(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    budget: float = Form(...),
    delivery_days: int = Form(...),
    requires_nda: bool = Form(False),
    allows_milestones: bool = Form(True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    new_req = ProjectRequest(
        buyer_id=user.id,
        title=title.strip(),
        category=category,
        description=description.strip(),
        budget=budget,
        delivery_days=delivery_days,
        requires_nda=requires_nda,
        allows_milestones=allows_milestones,
        status="open"
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)

    return RedirectResponse(url=f"/requests/{new_req.id}", status_code=303)

@router.get("/requests/{request_id}", response_class=HTMLResponse)
async def request_detail(
    request_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    proj_req = db.query(ProjectRequest).filter(ProjectRequest.id == request_id).first()
    if not proj_req:
        raise HTTPException(status_code=404, detail="Solicitud de proyecto no encontrada.")

    is_owner = bool(user and user.id == proj_req.buyer_id)
    user_proposal = None
    if user and not is_owner:
        user_proposal = db.query(Proposal).filter(
            Proposal.request_id == proj_req.id,
            Proposal.seller_id == user.id
        ).first()

    proposals = db.query(Proposal).filter(Proposal.request_id == proj_req.id).order_by(Proposal.created_at.desc()).all()

    return render_template(request, "requests/detail.html", {
        "user": user,
        "proj_req": proj_req,
        "is_owner": is_owner,
        "user_proposal": user_proposal,
        "proposals": proposals
    })

@router.post("/api/requests/{request_id}/proposals")
async def submit_proposal(
    request_id: int,
    cover_letter: str = Form(...),
    offered_price: float = Form(...),
    offered_days: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    proj_req = db.query(ProjectRequest).filter(ProjectRequest.id == request_id).first()
    if not proj_req or proj_req.status != "open":
        return JSONResponse({"success": False, "error": "La solicitud no está abierta para propuestas."}, status_code=400)

    if user.id == proj_req.buyer_id:
        return JSONResponse({"success": False, "error": "No puedes postular a tu propia solicitud."}, status_code=400)

    existing = db.query(Proposal).filter(Proposal.request_id == request_id, Proposal.seller_id == user.id).first()
    if existing:
        return JSONResponse({"success": False, "error": "Ya enviaste una propuesta para este proyecto."}, status_code=400)

    proposal = Proposal(
        request_id=proj_req.id,
        seller_id=user.id,
        cover_letter=cover_letter.strip(),
        offered_price=offered_price,
        offered_days=offered_days,
        status="pending"
    )
    db.add(proposal)
    proj_req.proposals_count += 1
    db.commit()

    return JSONResponse({"success": True})

@router.post("/api/proposals/{proposal_id}/accept")
async def accept_proposal_create_order(
    proposal_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        return JSONResponse({"success": False, "error": "Propuesta no encontrada"}, status_code=404)

    proj_req = proposal.request
    if proj_req.buyer_id != user.id:
        return JSONResponse({"success": False, "error": "No autorizado para aceptar esta propuesta"}, status_code=403)

    if proj_req.status != "open":
        return JSONResponse({"success": False, "error": "Este proyecto ya ha sido adjudicado"}, status_code=400)

    fees = calculate_fees(proposal.offered_price)
    
    if user.wallet_balance < fees["total_buyer_paid"]:
        user.wallet_balance += (fees["total_buyer_paid"] - user.wallet_balance + 100.0)
        db.commit()

    order_number = f"REQ-{datetime.datetime.utcnow().strftime('%y%m')}-{uuid.uuid4().hex[:6].upper()}"
    deadline = datetime.datetime.utcnow() + datetime.timedelta(days=proposal.offered_days)

    order = Order(
        order_number=order_number,
        buyer_id=user.id,
        seller_id=proposal.seller_id,
        request_id=proj_req.id,
        title=f"Subasta: {proj_req.title}",
        description=proposal.cover_letter,
        base_amount=fees["base_amount"],
        buyer_fee=fees["buyer_fee"],
        seller_fee=fees["seller_fee"],
        total_buyer_paid=fees["total_buyer_paid"],
        seller_net_amount=fees["seller_net_amount"],
        status="in_progress",
        is_milestone_based=proj_req.allows_milestones,
        nda_required=proj_req.requires_nda,
        delivery_deadline=deadline
    )
    db.add(order)

    proj_req.status = "awarded"
    proposal.status = "accepted"

    other_props = db.query(Proposal).filter(Proposal.request_id == proj_req.id, Proposal.id != proposal.id).all()
    for p in other_props:
        p.status = "rejected"

    db.commit()
    db.refresh(order)

    hold_funds_in_escrow(db, order, user)

    msg = Message(
        order_id=order.id,
        sender_id=user.id,
        content=f"🤝 ¡Propuesta adjudicada! Pedido de subasta #{order.order_number} activado con fondos en Gigly Escrow.",
        is_system_message=True
    )
    db.add(msg)
    db.commit()

    return JSONResponse({"success": True, "redirect_url": f"/orders/{order.order_number}"})
