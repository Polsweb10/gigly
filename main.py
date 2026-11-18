import os
import datetime
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db
from app.auth import get_current_user_optional
from app.models import Gig, User, ProjectRequest
from app.templating import render_template

# Import routers
from app.routers.auth_routes import router as auth_router
from app.routers.gigs_routes import router as gigs_router, CATEGORIES
from app.routers.orders_routes import router as orders_router
from app.routers.requests_routes import router as requests_router
from app.routers.chat_routes import router as chat_router
from app.routers.wallet_routes import router as wallet_router
from app.routers.analytics_routes import router as analytics_router
from app.routers.admin_routes import router as admin_router

app = FastAPI(
    title="Gigly - Marketplace de Servicios Freelance de Próxima Generación",
    description="Plataforma freelance avanzada con Gigly Escrow, pagos por hitos, bóveda con marca de agua, NDAs con un clic y chat con videollamadas.",
    version="1.0.0"
)

# Static and Upload mounts
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")

# Include Routers
app.include_router(auth_router)
app.include_router(gigs_router)
app.include_router(orders_router)
app.include_router(requests_router)
app.include_router(chat_router)
app.include_router(wallet_router)
app.include_router(analytics_router)
app.include_router(admin_router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
async def home_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user_optional(request, db)
    featured_gigs = db.query(Gig).filter(Gig.is_active == True).order_by(Gig.rating_avg.desc()).limit(8).all()
    recent_requests = db.query(ProjectRequest).filter(ProjectRequest.status == "open").order_by(ProjectRequest.created_at.desc()).limit(4).all()
    total_freelancers = db.query(User).count()
    total_gigs = db.query(Gig).count()

    return render_template(request, "index.html", {
        "user": user,
        "categories": CATEGORIES,
        "featured_gigs": featured_gigs,
        "recent_requests": recent_requests,
        "total_freelancers": max(total_freelancers, 120),
        "total_gigs": max(total_gigs, 45)
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
