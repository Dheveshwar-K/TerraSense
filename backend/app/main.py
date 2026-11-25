import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import (
    alerts,
    analytics,
    audit,
    auth,
    complaints,
    correlations,
    investigations,
    lines,
    parameters,
    rejections,
    reports,
    sand_batches,
    sand_tests,
    spc,
    system,
    users,
)
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.migrations import run_non_destructive_migrations
from app.services.seed_service import seed_foundry_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("PS010-Quality4.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Validating runtime security configuration (env=%s)...", settings.ENVIRONMENT)
    settings.validate_runtime_settings()

    logger.info("Running non-destructive schema migrations...")
    applied = run_non_destructive_migrations(engine)
    if applied:
        logger.info("Applied migrations: %s", applied)

    if settings.is_demo_enabled():
        db = SessionLocal()
        try:
            logger.info("Demo mode enabled: verifying foundry demo dataset...")
            seed_foundry_data(db, force=False)
        finally:
            db.close()
    else:
        logger.info("Demo mode disabled: skipping demo data seeding.")

    yield
    logger.info("Shutting down PS-010 Application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Quality 4.0 Integrated Digital Sand Quality Management, Real-time SPC, "
        "Rejection Analytics, and Defect Correlation System for Foundries (D1, D2, D3, D4)"
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)


@app.middleware("http")
async def security_and_observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request payload exceeds maximum allowed size."},
                )
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s [request_id=%s]", request.method, request.url.path, request_id)
        if settings.ENVIRONMENT == "production":
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if request.url.path.startswith("/api/auth"):
        response.headers["Cache-Control"] = "no-store"

    # Safe structured request log (never logs query strings or auth headers)
    logger.info(
        "method=%s path=%s status=%s duration_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["User Management"])
app.include_router(lines.router, prefix="/api/lines", tags=["Production Lines"])
app.include_router(parameters.router, prefix="/api/parameters", tags=["Parameters & Specifications"])
app.include_router(sand_tests.router, prefix="/api/sand-tests", tags=["Digital Sand Tests"])
app.include_router(sand_batches.router, prefix="/api/sand-batches", tags=["Sand Batches"])
app.include_router(spc.router, prefix="/api/spc", tags=["Statistical Process Control (SPC)"])
app.include_router(rejections.router, prefix="/api/rejections", tags=["Casting Rejections & Pareto"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Dashboard Analytics"])
app.include_router(correlations.router, prefix="/api/correlations", tags=["Correlation & Root Cause Engine"])
app.include_router(investigations.router, prefix="/api/investigations", tags=["Root Cause Investigations"])
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
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/health")
def health_check():
    """Liveness endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": "PS-010 Quality 4.0 Backend",
        "version": settings.VERSION,
    }


@app.get("/api/ready")
def readiness_check():
    """Readiness endpoint verifying live database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database readiness check failed")
    return {
        "status": "ready",
        "database": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
