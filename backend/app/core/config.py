import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME: str = "PS-010: Digital Sand Quality Management & Rejection Analytics"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # SQLite file path in backend directory by default, supports PostgreSQL via env
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'foundry_quality.db'}"
    )
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "FOUNDRY-QUALITY-4.0-PS010-SUPER-SECURE-KEY-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    DEMO_MODE: bool = True

settings = Settings()
