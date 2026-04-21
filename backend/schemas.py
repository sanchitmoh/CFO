"""
AI CFO — Pydantic Schemas
All request/response models aligned with frontend types.ts contracts.
"""
import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr


# ═══════════════════════════════════════════════════════════════════
# AUTH / USER
# ═══════════════════════════════════════════════════════════════════

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    workspace_id: uuid.UUID
    avatar_url: Optional[str] = None
    is_active: bool = True
    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class InviteRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "viewer"


class RoleUpdateRequest(BaseModel):
    role: str


# ═══════════════════════════════════════════════════════════════════
# WORKSPACE
# ═══════════════════════════════════════════════════════════════════

class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    industry: str
    currency: str
    is_demo: bool
    model_config = {"from_attributes": True}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════

class TransactionCreate(BaseModel):
    date: datetime
    description: str
    amount: float
    category: str
    type: str  # income | expense
    account: str = "Main Account"
    vendor: Optional[str] = None
    notes: Optional[str] = None


class TransactionOut(BaseModel):
    id: uuid.UUID
    date: datetime
    description: str
    amount: float
    category: str
    type: str
    account: str
    vendor: Optional[str] = None
    is_anomaly: bool = False
    anomaly_score: Optional[float] = None
    source: str = "manual"
    created_at: datetime
    model_config = {"from_attributes": True}


class PaginatedTransactions(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    per_page: int
    pages: int


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════

class CategoryAmount(BaseModel):
    category: str
    amount: float


class DashboardSummary(BaseModel):
    total_income: float
    total_expenses: float
    net_cash_flow: float
    transaction_count: int
    burn_rate: float
    runway_months: float
    budget_utilization: float
    active_alerts: int
    cash_balance: float
    monthly_income: list[float]
    monthly_expenses: list[float]
    top_categories: list[CategoryAmount]
    recent_transactions: list[TransactionOut]
    period_months: int


class CashFlowPoint(BaseModel):
    period: str
    income: float
    expenses: float
    net: float


class ExpenseBreakdownItem(BaseModel):
    category: str
    total: float
    percentage: float


# ═══════════════════════════════════════════════════════════════════
# BUDGETS
# ═══════════════════════════════════════════════════════════════════

class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float
    alert_threshold: float = 0.8
    month: Optional[str] = None  # YYYY-MM, defaults to current


class BudgetOut(BaseModel):
    id: uuid.UUID
    category: str
    monthly_limit: float
    alert_threshold: float
    current_spend: float
    percentage_used: float
    status: str  # on_track | warning | over_budget
    month: str
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# GOALS
# ═══════════════════════════════════════════════════════════════════

class GoalCreate(BaseModel):
    title: str
    target_value: float
    metric_type: str  # revenue | savings | expense_reduction
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    status: Optional[str] = None
    deadline: Optional[date] = None


class GoalOut(BaseModel):
    id: uuid.UUID
    title: str
    target_value: float
    current_value: float
    metric_type: str
    deadline: Optional[datetime] = None
    status: str
    progress_pct: float  # computed
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════════════

class AlertOut(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    severity: str  # info | warning | critical
    category: str
    action_url: Optional[str] = None
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class AlertRuleCreate(BaseModel):
    rule_type: str
    threshold_value: float
    notify_email: bool = True
    notify_slack: bool = False
    slack_webhook: Optional[str] = None


class AlertRuleOut(BaseModel):
    id: uuid.UUID
    rule_type: str
    threshold_value: float
    is_enabled: bool
    notify_email: bool
    notify_slack: bool
    slack_webhook_masked: Optional[str] = None  # e.g. "http...xxxx" — never the full URL
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# FORECASTING
# ═══════════════════════════════════════════════════════════════════

class ForecastPoint(BaseModel):
    period: str
    projected_income: float
    projected_expenses: float
    projected_net: float
    cumulative_net: float
    confidence: float
    confidence_lower: float
    confidence_upper: float


class ForecastResponse(BaseModel):
    scenario: str
    months_ahead: int
    historical_months: int
    data_points: list[ForecastPoint]
    model_version: str = "v1_linear"


# ═══════════════════════════════════════════════════════════════════
# CHAT
# ═══════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[uuid.UUID] = None


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime
    last_active_at: datetime
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []
    suggested_actions: list[str] = []
    confidence: str = "medium"


# ═══════════════════════════════════════════════════════════════════
# ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════════════

class AnomalyOut(BaseModel):
    id: uuid.UUID
    date: datetime
    description: str
    amount: float
    category: str
    type: str
    account: str
    anomaly_score: float
    reason: str
    model_config = {"from_attributes": True}


class ScanResult(BaseModel):
    scanned: int
    anomalies_found: int
    anomalies: list[AnomalyOut]


# ═══════════════════════════════════════════════════════════════════
# HEALTH SCORE
# ═══════════════════════════════════════════════════════════════════

class ScoreComponent(BaseModel):
    name: str
    score: float
    max_score: float = 100
    description: str
    status: str  # excellent | good | fair | poor


class HealthScoreResponse(BaseModel):
    overall_score: float
    grade: str
    stage: str = "growth"  # early | growth | mature
    components: list[ScoreComponent]
    recommendations: list[str]
    computed_at: datetime


# ═══════════════════════════════════════════════════════════════════
# REPORTS
# ═══════════════════════════════════════════════════════════════════

class CategorySummary(BaseModel):
    category: str
    total: float
    count: int


class ReportSummary(BaseModel):
    period_start: date
    period_end: date
    total_income: float
    total_expenses: float
    net_cash_flow: float
    transaction_count: int
    expense_by_category: list[CategorySummary]
    top_vendors: list[dict]


# ═══════════════════════════════════════════════════════════════════
# CALCULATOR (Feature B)
# ═══════════════════════════════════════════════════════════════════

class AffordabilityRequest(BaseModel):
    expense_name: str
    amount: float
    frequency: str = "one_time"  # one_time | monthly | annual


class AffordabilityResponse(BaseModel):
    can_afford: bool
    current_runway_months: float
    projected_runway_months: float
    current_balance_3m: float
    projected_balance_3m: float
    break_even_revenue: Optional[float] = None
    ai_suggestion: str


# ═══════════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════════

class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_email: str
    user_name: str
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class PaginatedAuditLogs(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    per_page: int


# ═══════════════════════════════════════════════════════════════════
# BENCHMARKS (Feature C)
# ═══════════════════════════════════════════════════════════════════

class BenchmarkInsight(BaseModel):
    metric_name: str
    your_value: float
    benchmark_value: float
    unit: str
    delta_pct: float
    insight: str
    status: str  # above | below | on_par
