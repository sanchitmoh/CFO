"""
AI CFO — FastAPI Application Entry Point
All routers wired, CORS configured, lifespan for DB init + scheduled jobs.
SEC-FIX: Added security headers middleware.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from database import engine
from telemetry import setup_telemetry

logger = logging.getLogger(__name__)

# ── Import all routers ────────────────────────────────────────────
from routers import (
    auth as auth_router,
    dashboard as dashboard_router,
    transactions as transactions_router,
    budgets as budgets_router,
    alerts as alerts_router,
    chat as chat_router,
    forecasting as forecasting_router,
    anomaly as anomaly_router,
    health_score as health_score_router,
    reports as reports_router,
    settings as settings_router,
    calculator as calculator_router,
    goals as goals_router,
    audit as audit_router,
    benchmarks as benchmarks_router,
    onboarding as onboarding_router,
    plaid as plaid_router,
    semantic_search as semantic_search_router,
    # CRIT-001: password_policy router removed — unused dead code with live attack surface.
    # Auth is handled by Clerk. If custom auth is needed later, rewrite with DB-persisted config.
    compliance as compliance_router,
)

# ── SEC-FIX: Security Headers Middleware ──────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent MIME-sniffing attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Strict Transport Security (HSTS) - only in production with HTTPS
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.clerk.com https://api.openai.com; "
            "frame-ancestors 'none';"
        )
        
        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


# ── API Versioning: Backward Compatibility Middleware ────────────
class BackwardCompatibilityMiddleware(BaseHTTPMiddleware):
    """Route legacy /api/* requests to /api/v1/* for backward compatibility."""
    
    async def dispatch(self, request: Request, call_next):
        # Check if this is a legacy API request (starts with /api/ but not /api/v1/)
        if (request.url.path.startswith("/api/") and 
            not request.url.path.startswith("/api/v1/") and
            not request.url.path == "/api/health"):  # Preserve health endpoint
            
            # Rewrite the path to use v1 versioning
            original_path = request.url.path
            versioned_path = original_path.replace("/api/", "/api/v1/", 1)
            
            # Create a new request with the versioned path
            request.scope["path"] = versioned_path
            request.scope["raw_path"] = versioned_path.encode()
            
            # Log the redirect for debugging (optional)
            logger.debug(f"API versioning redirect: {original_path} -> {versioned_path}")
        
        response = await call_next(request)
        return response

# ── EXT-002: Periodic alert scheduler ────────────────────────────
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run Alembic migrations on startup, then start scheduler."""
    # L-003: Use versioned Alembic migrations instead of create_all
    # Note: Migrations should be run manually with: alembic upgrade head
    # Skipping auto-migrations on startup to avoid blocking
    
    logger.info("Skipping auto-migrations - run 'alembic upgrade head' manually")

    # CONFIG-001: Warn if localhost CORS origins in production
    if not settings.DEBUG and any("localhost" in o for o in settings.CORS_ORIGINS):
        logger.critical(
            "CONFIG-001: CORS_ORIGINS contains localhost in production mode! "
            "Frontend will be blocked. Set CORS_ORIGINS in .env to your production domain."
        )
    
    # CONFIG-002: Warn if OTEL enabled but endpoint unreachable
    if settings.OTEL_ENABLED:
        if "localhost" in settings.OTEL_EXPORTER_OTLP_ENDPOINT or "127.0.0.1" in settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            logger.warning(
                "CONFIG-002: OTEL_ENABLED=true but endpoint is localhost (%s). "
                "Telemetry will fail in production. Set OTEL_EXPORTER_OTLP_ENDPOINT to your collector.",
                settings.OTEL_EXPORTER_OTLP_ENDPOINT
            )

    # EXT-002: Schedule periodic alert evaluation across all workspaces.
    # Lazy import to avoid circular dependencies at module load time.
    from services.alert_engine import run_all_workspace_alerts

    scheduler.add_job(
        run_all_workspace_alerts,
        "interval",
        hours=6,
        id="alert_engine_sweep",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started — alert sweep every 6 hours")

    yield

    scheduler.shutdown(wait=False)
    logger.info("APScheduler shut down")


app = FastAPI(
    title="AI CFO Platform",
    description="Intelligent financial management for SMBs",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Observability (ADVANCE-001) ───────────────────────────────────
setup_telemetry(app)

# ── SEC-FIX: Add security headers middleware ──────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ── API Versioning: Add backward compatibility middleware ──────────
app.add_middleware(BackwardCompatibilityMiddleware)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register ALL routers with v1 versioning ──────────────────────
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dashboard_router.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(transactions_router.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(budgets_router.router, prefix="/api/v1/budgets", tags=["Budgets"])
app.include_router(alerts_router.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(chat_router.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(forecasting_router.router, prefix="/api/v1/forecasting", tags=["Forecasting"])
app.include_router(anomaly_router.router, prefix="/api/v1/anomaly", tags=["Anomaly Detection"])
app.include_router(health_score_router.router, prefix="/api/v1/health-score", tags=["Health Score"])
app.include_router(reports_router.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(calculator_router.router, prefix="/api/v1/calculator", tags=["Calculator"])
app.include_router(goals_router.router, prefix="/api/v1/goals", tags=["Goals"])
app.include_router(audit_router.router, prefix="/api/v1/audit", tags=["Audit Log"])
app.include_router(benchmarks_router.router, prefix="/api/v1/benchmarks", tags=["Benchmarks"])
app.include_router(onboarding_router.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
app.include_router(plaid_router.router, prefix="/api/v1/plaid", tags=["Plaid"])
app.include_router(semantic_search_router.router, prefix="/api/v1/search", tags=["Semantic Search"])
# CRIT-001: password_policy router removed — see import block comment
app.include_router(compliance_router.router, prefix="/api/v1/compliance", tags=["GDPR/CCPA Compliance"])


@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Keep legacy health endpoint for backward compatibility
@app.get("/api/health", tags=["System"])
async def legacy_health_check():
    return {"status": "healthy", "version": "1.0.0"}
