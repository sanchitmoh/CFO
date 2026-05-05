"""
AI CFO — Pydantic Schemas
All request/response models aligned with frontend types.ts contracts.
"""
import uuid
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, constr
from decimal import Decimal


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
    full_name: constr(min_length=1, max_length=255) = Field(..., description="Full name of the invitee")  # type: ignore
    role: str = Field("viewer", pattern="^(owner|admin|cfo|accountant|investor|employee|viewer)$")


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|cfo|accountant|investor|employee|viewer)$")


# ═══════════════════════════════════════════════════════════════════
# WORKSPACE
# ═══════════════════════════════════════════════════════════════════

class AlertSettingsUpdate(BaseModel):
    """Payload for PUT /api/settings/alerts — all fields optional for partial update."""
    low_cash_threshold: Optional[float] = None
    high_expense_threshold: Optional[float] = None
    anomaly_sensitivity: Optional[float] = None  # z-score multiplier


# ═══════════════════════════════════════════════════════════════════
# PASSWORD POLICY (COMPLIANCE-003)
# ═══════════════════════════════════════════════════════════════════

class PasswordValidationRequest(BaseModel):
    """Request to validate a password against current policy."""
    password: str = Field(..., min_length=1, max_length=256)
    user_info: Optional[dict] = Field(None, description="Optional user info to check against")


class PasswordValidationResponse(BaseModel):
    """Response from password validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    strength_score: int = Field(..., ge=0, le=100)


class PasswordPolicyInfo(BaseModel):
    """Current password policy configuration."""
    enabled: bool
    requirements: dict


class PasswordPolicyUpdateRequest(BaseModel):
    """Request to update password policy settings (admin only)."""
    enabled: Optional[bool] = None
    min_length: Optional[int] = Field(None, ge=1, le=256)
    max_length: Optional[int] = Field(None, ge=8, le=512)
    require_uppercase: Optional[bool] = None
    require_lowercase: Optional[bool] = None
    require_numbers: Optional[bool] = None
    require_special_chars: Optional[bool] = None
    min_special_chars: Optional[int] = Field(None, ge=0, le=10)
    prevent_common_passwords: Optional[bool] = None
    prevent_user_info: Optional[bool] = None
    email_enabled: Optional[bool] = None
    email_addresses: Optional[list[str]] = None
    slack_enabled: Optional[bool] = None
    slack_webhook_url: Optional[str] = None


class AlertSettingsOut(BaseModel):
    """Response for GET /api/settings/alerts."""
    low_cash_threshold: float = 5000.0
    high_expense_threshold: float = 10000.0
    anomaly_sensitivity: float = 2.5
    email_enabled: bool = False


# ═══════════════════════════════════════════════════════════════════
# GDPR/CCPA COMPLIANCE (COMPLIANCE-004)
# ═══════════════════════════════════════════════════════════════════

class DataExportRequest(BaseModel):
    """Request for GDPR Article 20 data export."""
    format: Optional[str] = Field("json", pattern="^(json|csv)$")
    include_metadata: Optional[bool] = True
    email_delivery: Optional[bool] = False  # Future: email the export file


class DataExportResponse(BaseModel):
    """Response for data export request."""
    export_id: uuid.UUID
    status: str = "completed"
    format: str
    file_size_bytes: int
    created_at: datetime
    expires_at: datetime
    download_url: Optional[str] = None  # Future: signed URL for download


class DataDeletionRequest(BaseModel):
    """Request for GDPR Article 17 data deletion."""
    confirmation_text: str = Field(..., description="Must match 'DELETE MY DATA' exactly")
    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for deletion")
    
    @field_validator('confirmation_text')
    @classmethod
    def validate_confirmation(cls, v):
        if v != "DELETE MY DATA":
            raise ValueError("Confirmation text must be exactly 'DELETE MY DATA'")
        return v


class DataDeletionResponse(BaseModel):
    """Response for data deletion request."""
    deletion_id: uuid.UUID
    status: str = "scheduled"  # scheduled | in_progress | completed | failed
    scheduled_at: datetime
    grace_period_ends_at: Optional[datetime] = None
    message: str


class ConsentRequest(BaseModel):
    """Request to update user consent preferences."""
    data_processing: bool = Field(..., description="Consent to data processing")
    analytics: Optional[bool] = Field(True, description="Consent to analytics")
    marketing: Optional[bool] = Field(False, description="Consent to marketing communications")
    third_party_sharing: Optional[bool] = Field(False, description="Consent to third-party data sharing")


class ConsentResponse(BaseModel):
    """Current user consent status."""
    user_id: uuid.UUID
    data_processing: bool
    analytics: bool
    marketing: bool
    third_party_sharing: bool
    consent_date: datetime
    last_updated: datetime
    ip_address_hash: Optional[str] = None  # Hashed IP for audit trail


class ConsentWithdrawalRequest(BaseModel):
    """Request to withdraw consent."""
    consent_types: List[str] = Field(..., description="Types of consent to withdraw")
    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for withdrawal")


class RetentionPolicyInfo(BaseModel):
    """Information about data retention policies."""
    policy_name: str
    description: str
    retention_days: int
    applies_to: List[str]  # List of data types this policy applies to
    last_cleanup: Optional[datetime] = None
    next_cleanup: Optional[datetime] = None


class RetentionPolicyResponse(BaseModel):
    """Response with all retention policies."""
    policies: List[RetentionPolicyInfo]
    total_policies: int
    cleanup_enabled: bool


class ComplianceStatusResponse(BaseModel):
    """Overall compliance status for the user/workspace."""
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    gdpr_compliant: bool
    ccpa_compliant: bool
    data_export_available: bool
    data_deletion_available: bool
    consent_management_active: bool
    retention_policies_active: bool
    last_export: Optional[datetime] = None
    consent_status: Optional[ConsentResponse] = None
    email_addresses: list[str] = []
    slack_enabled: bool = False
    slack_webhook_url: Optional[str] = None
    model_config = {"from_attributes": True}


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    industry: str
    currency: str
    is_demo: bool
    alert_config: Optional[dict] = None
    model_config = {"from_attributes": True}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════

class TransactionCreate(BaseModel):
    date: datetime = Field(..., description="Transaction date")
    description: constr(min_length=1, max_length=500) = Field(..., description="Transaction description")  # type: ignore
    amount: float = Field(..., gt=0, le=999999999.99, description="Transaction amount (must be positive)")
    category: constr(min_length=1, max_length=100) = Field(..., description="Transaction category")  # type: ignore
    type: str = Field(..., pattern="^(income|expense)$", description="Transaction type")
    account: constr(max_length=100) = Field("Main Account", description="Account name")  # type: ignore
    vendor: Optional[constr(max_length=200)] = None  # type: ignore
    notes: Optional[constr(max_length=2000)] = None  # type: ignore
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: datetime) -> datetime:
        """Ensure date is not in the far future or past."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if v.year < 1900 or v.year > 2100:
            raise ValueError("Date must be between 1900 and 2100")
        if v > now.replace(year=now.year + 1):
            raise ValueError("Date cannot be more than 1 year in the future")
        return v


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
    category: constr(min_length=1, max_length=100) = Field(..., description="Budget category")  # type: ignore
    monthly_limit: float = Field(..., gt=0, le=999999999.99, description="Monthly budget limit")
    alert_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Alert threshold (0.0-1.0)")
    month: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")


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
    title: constr(min_length=1, max_length=255) = Field(..., description="Goal title")  # type: ignore
    target_value: float = Field(..., gt=0, le=999999999.99, description="Target value")
    metric_type: str = Field(..., pattern="^(revenue|savings|expense_reduction)$", description="Metric type")
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|cancelled|on_hold)$")  # LOW-006: Add validation
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
    message: constr(min_length=1, max_length=2000) = Field(..., description="Chat message")  # type: ignore
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
# FILE UPLOADS (FILE-001)
# ═══════════════════════════════════════════════════════════════════

class FileUploadOut(BaseModel):
    id: uuid.UUID
    filename: str
    file_size: int
    row_count: int
    error_count: int
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


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
