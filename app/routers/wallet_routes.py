import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, WalletTransaction
from app.auth import get_current_user_optional, get_current_user
from app.templating import render_template

router = APIRouter(tags=["Wallet"])

@router.get("/wallet", response_class=HTMLResponse)
async def wallet_view(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/wallet", status_code=303)

    transactions = db.query(WalletTransaction).filter(
        WalletTransaction.user_id == user.id
    ).order_by(WalletTransaction.created_at.desc()).all()

    total_deposited = sum(t.amount for t in transactions if t.type == "deposit")
    total_earned = sum(t.amount for t in transactions if t.type == "escrow_release")

    return render_template(request, "dashboard/wallet.html", {
        "user": user,
        "transactions": transactions,
        "total_deposited": total_deposited,
        "total_earned": total_earned
    })

@router.post("/api/wallet/deposit")
async def deposit_funds(
    amount: float = Form(...),
    payment_method: str = Form("card"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if amount <= 0:
        return JSONResponse({"success": False, "error": "El monto debe ser mayor a 0"}, status_code=400)

    user.wallet_balance = round(user.wallet_balance + amount, 2)
    
    tx = WalletTransaction(
        user_id=user.id,
        type="deposit",
        amount=amount,
        description=f"Recarga de saldo vía {payment_method.capitalize()}"
    )
    db.add(tx)
    db.commit()

    return JSONResponse({"success": True, "new_balance": user.wallet_balance})

@router.post("/api/wallet/withdraw")
async def withdraw_funds(
    amount: float = Form(...),
    payout_account: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if amount <= 0:
        return JSONResponse({"success": False, "error": "Monto inválido"}, status_code=400)

    if amount > user.wallet_balance:
        return JSONResponse({"success": False, "error": "Saldo insuficiente para retirar"}, status_code=400)

    user.wallet_balance = round(user.wallet_balance - amount, 2)
    
    tx = WalletTransaction(
        user_id=user.id,
        type="withdrawal",
        amount=-amount,
        description=f"Retiro solicitado a cuenta {payout_account[:4]}****"
    )
    db.add(tx)
    db.commit()

    return JSONResponse({"success": True, "new_balance": user.wallet_balance})
