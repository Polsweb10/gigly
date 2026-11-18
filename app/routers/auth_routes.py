import json
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, WalletTransaction
from app.auth import hash_password, verify_password, create_access_token, get_current_user, get_current_user_optional
from app.templating import render_template

router = APIRouter(tags=["Auth"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return render_template(request, "auth/login.html", {"user": None, "error": None})

@router.post("/login")
async def login_action(
    request: Request,
    response: Response,
    username_or_email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return render_template(
            request,
            "auth/login.html",
            {"user": None, "error": "Credenciales incorrectas. Verifica tu usuario o contraseña."},
            status_code=400
        )

    token = create_access_token({"sub": str(user.id), "username": user.username})
    redirect_target = request.query_params.get("next", "/")
    res = RedirectResponse(url=redirect_target, status_code=303)
    res.set_cookie(
        key="gigly_session",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax"
    )
    return res

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return render_template(request, "auth/register.html", {"user": None, "error": None})

@router.post("/register")
async def register_action(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    initial_mode: str = Form("buyer"),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing:
        return render_template(
            request,
            "auth/register.html",
            {"user": None, "error": "El usuario o correo electrónico ya se encuentra registrado."},
            status_code=400
        )

    hashed = hash_password(password)
    new_user = User(
        username=username.strip().lower(),
        email=email.strip().lower(),
        full_name=full_name.strip(),
        password_hash=hashed,
        current_mode=initial_mode if initial_mode in ["buyer", "seller"] else "buyer",
        wallet_balance=150.0  # Bono inicial
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Initial bonus transaction
    tx = WalletTransaction(
        user_id=new_user.id,
        type="deposit",
        amount=150.0,
        description="Bono de bienvenida Gigly para exploración y pedidos demo"
    )
    db.add(tx)
    db.commit()

    token = create_access_token({"sub": str(new_user.id), "username": new_user.username})
    res = RedirectResponse(url="/", status_code=303)
    res.set_cookie(
        key="gigly_session",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax"
    )
    return res

@router.get("/logout")
async def logout():
    res = RedirectResponse(url="/login", status_code=303)
    res.delete_cookie("gigly_session")
    return res

@router.post("/api/auth/switch-mode")
async def switch_mode(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        data = await request.json()
        new_mode = data.get("mode")
    except Exception:
        new_mode = "seller" if user.current_mode == "buyer" else "buyer"

    if new_mode in ["buyer", "seller"]:
        user.current_mode = new_mode
        db.commit()
        return JSONResponse({"success": True, "current_mode": user.current_mode})
    
    return JSONResponse({"success": False, "error": "Modo inválido"}, status_code=400)
