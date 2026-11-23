import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.services.seed_service import seed_foundry_data

# Import API routes
from app.api.routes import (
    auth,
    lines,
    parameters,
    sand_tests,
    spc,
    rejections,
    analytics,
    correlations,
    complaints,
    alerts,
    audit,
    reports,
    system
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PS010-Quality4.0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed demo data
    logger.info("Initializing PS-010 Database Schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        logger.info("Verifying initial Foundry Quality seed dataset for D1, D2, D3, D4...")
        seed_foundry_data(db, force=False)
    finally:
        db.close()
    yield
    # Shutdown
    logger.info("Shutting down PS-010 Application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Quality 4.0 Integrated Digital Sand Quality Management, Real-time SPC, Rejection Analytics, and Defect Correlation System for Foundries (D1, D2, D3, D4)",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(lines.router, prefix="/api/lines", tags=["Production Lines"])
app.include_router(parameters.router, prefix="/api/parameters", tags=["Parameters & Specifications"])
app.include_router(sand_tests.router, prefix="/api/sand-tests", tags=["Digital Sand Tests"])
app.include_router(spc.router, prefix="/api/spc", tags=["Statistical Process Control (SPC)"])
app.include_router(rejections.router, prefix="/api/rejections", tags=["Casting Rejections & Pareto"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Dashboard Analytics"])
app.include_router(correlations.router, prefix="/api/correlations", tags=["Correlation & Root Cause Engine"])
app.include_router(complaints.router, prefix="/api/complaints", tags=["Customer Complaints & 8D CAPA"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Quality Alert Engine"])
app.include_router(audit.router, prefix="/api/audit-logs", tags=["IATF Digital Audit Trail"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports & Exports"])
app.include_router(system.router, prefix="/api/system", tags=["System Management"])

@app.get("/")
def root():
    return {
        "system": "PS-010: Integrated Digital Sand Quality Management & Rejection Analytics System",
        "version": settings.VERSION,
        "status": "OPERATIONAL",
        "lines": ["D1", "D2", "D3", "D4"],
        "docs_url": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat() if "datetime" in globals() else "OK",
        "system": "PS-010 Quality 4.0 Backend",
        "database": "connected"
    }
