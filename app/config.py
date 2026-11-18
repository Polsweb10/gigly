import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Gigly"
    APP_ENV: str = "development"
    SECRET_KEY: str = "gigly-super-secret-key-change-me-in-production-2026-secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./gigly.db"
    
    # Platform Commissions (%)
    PLATFORM_SELLER_FEE_PERCENT: float = 10.0  # 10% taken from seller
    PLATFORM_BUYER_FEE_PERCENT: float = 3.0    # 3% service fee added to buyer
    
    # Directories
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    UPLOAD_GIGS_DIR: Path = BASE_DIR / "uploads" / "gigs"
    UPLOAD_DELIVERIES_DIR: Path = BASE_DIR / "uploads" / "deliveries"
    UPLOAD_WATERMARKED_DIR: Path = BASE_DIR / "uploads" / "watermarked"
    
    # URLs
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure directories exist
for folder in [
    settings.UPLOAD_DIR,
    settings.UPLOAD_GIGS_DIR,
    settings.UPLOAD_DELIVERIES_DIR,
    settings.UPLOAD_WATERMARKED_DIR
]:
    folder.mkdir(parents=True, exist_ok=True)
