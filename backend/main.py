"""
AI CFO — FastAPI Application Entry Point
All routers wired, CORS configured, lifespan for DB init.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import engine, Base
from telemetry import setup_telemetry

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
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (dev only — use Alembic in prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="AI CFO Platform",
    description="Intelligent financial management for SMBs",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Observability (ADVANCE-001) ───────────────────────────────────
setup_telemetry(app)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register ALL routers ─────────────────────────────────────────
app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dashboard_router.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(transactions_router.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(budgets_router.router, prefix="/api/budgets", tags=["Budgets"])
app.include_router(alerts_router.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["Chat"])
app.include_router(forecasting_router.router, prefix="/api/forecasting", tags=["Forecasting"])
app.include_router(anomaly_router.router, prefix="/api/anomaly", tags=["Anomaly Detection"])
app.include_router(health_score_router.router, prefix="/api/health-score", tags=["Health Score"])
app.include_router(reports_router.router, prefix="/api/reports", tags=["Reports"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(calculator_router.router, prefix="/api/calculator", tags=["Calculator"])
app.include_router(goals_router.router, prefix="/api/goals", tags=["Goals"])
app.include_router(audit_router.router, prefix="/api/audit", tags=["Audit Log"])
app.include_router(benchmarks_router.router, prefix="/api/benchmarks", tags=["Benchmarks"])
app.include_router(onboarding_router.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(plaid_router.router, prefix="/api/plaid", tags=["Plaid"])
app.include_router(semantic_search_router.router, prefix="/api/search", tags=["Semantic Search"])


@app.get("/api/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
