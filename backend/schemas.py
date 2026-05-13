"""
AI CFO — Pydantic Schemas
All request/response models aligned with frontend types.ts contracts.
"""
import uuid
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, constr, computed_field
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
    currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$")


# ═══════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ═══════════════════════════════════════════════════════════════════

class TransactionCreate(BaseModel):
    date: datetime = Field(..., description="Transaction date")
    description: constr(min_length=1, max_length=500) = Field(..., description="Transaction description")  # type: ignore
    amount: float = Field(..., gt=0, le=999999999.99, description="Transaction amount (must be positive)")
    currency_code: str = Field("USD", min_length=3, max_length=3, description="ISO Currency Code")
    amount_original: Optional[float] = None
    exchange_rate: Optional[float] = None
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
    currency_code: str
    amount_original: Optional[float] = None
    exchange_rate: Optional[float] = None
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
    base_currency: str = "USD"
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


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — VENDOR MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class VendorContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_primary: bool = False

class VendorContactOut(VendorContactCreate):
    id: uuid.UUID
    vendor_id: uuid.UUID
    created_at: datetime
    model_config = {"from_attributes": True}

class VendorCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: int = 30
    category: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: Optional[int] = None
    category: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class VendorOut(BaseModel):
    id: uuid.UUID
    name: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: int
    category: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    contacts: list[VendorContactOut] = []
    total_spent: float = 0.0
    transaction_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class VendorSpendAnalysis(BaseModel):
    vendor_name: str
    total_spend: float
    transaction_count: int
    avg_transaction: float
    last_transaction_date: Optional[str] = None
    category: Optional[str] = None

class DuplicateVendorResult(BaseModel):
    vendor_a: str
    vendor_b: str
    similarity_score: float


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — TAX MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class TaxCategoryCreate(BaseModel):
    category: str
    tax_code: str = "non_deductible"
    deduction_rate: float = 0.0
    jurisdiction: str = "IN"
    notes: Optional[str] = None

class TaxCategoryOut(BaseModel):
    id: uuid.UUID
    category: str
    tax_code: str
    deduction_rate: float
    jurisdiction: str
    notes: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class TaxEstimateCreate(BaseModel):
    quarter: str  # e.g. "2026-Q1"
    jurisdiction: str = "IN"

class TaxEstimateUpdate(BaseModel):
    status: Optional[str] = None
    paid_date: Optional[datetime] = None

class TaxEstimateOut(BaseModel):
    id: uuid.UUID
    quarter: str
    jurisdiction: str
    taxable_income: float
    estimated_tax: float
    effective_rate: float
    deductions_total: float
    status: str
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}

    # Computed aliases the frontend expects
    @computed_field  # type: ignore[prop-decorator]
    @property
    def jurisdiction_code(self) -> str:
        return self.jurisdiction

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gross_income(self) -> float:
        return self.taxable_income + self.deductions_total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_deductions(self) -> float:
        return self.deductions_total

class TaxJurisdictionCreate(BaseModel):
    name: str
    code: str
    tax_rates_json: Optional[dict] = None
    filing_frequency: str = "quarterly"

class TaxJurisdictionOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    tax_rates_json: Optional[dict] = None
    filing_frequency: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class TaxReportResponse(BaseModel):
    period_start: str
    period_end: str
    jurisdiction: str
    total_income: float
    total_expenses: float
    deductible_expenses: float
    taxable_income: float
    estimated_tax: float
    effective_rate: float
    categories: list[dict]


# ── External Tax Calculation API Schemas ─────────────────────────

class IndiaTaxCalculationRequest(BaseModel):
    """Calculate India income tax via FinCalculator.in API."""
    gross_income: float = Field(..., gt=0, description="Annual gross income in ₹")
    regime: str = Field("new-2026-27", description="Tax regime: old, new-2024-25, new-2025-26, new-2026-27")
    apply_standard_deduction: bool = Field(True, description="Apply standard deduction")

class IndiaHRACalculationRequest(BaseModel):
    """Calculate HRA exemption under Section 10(13A)."""
    basic_salary: float = Field(..., gt=0, description="Annual basic + DA in ₹")
    hra_received: float = Field(..., gt=0, description="Annual HRA received in ₹")
    rent_paid: float = Field(..., gt=0, description="Annual rent paid in ₹")
    is_metro: bool = Field(True, description="Metro city (50% cap) vs non-metro (40%)")

class IndiaGratuityCalculationRequest(BaseModel):
    """Calculate gratuity under Payment of Gratuity Act, 1972."""
    monthly_basic: float = Field(..., gt=0, description="Last drawn monthly basic + DA in ₹")
    years_of_service: int = Field(..., gt=0, description="Years of continuous service")
    covered_by_act: bool = Field(True, description="Employer has ≥10 employees")

class USTaxCalculationRequest(BaseModel):
    """Calculate US self-employment tax via rel.tax API."""
    income: float = Field(..., gt=0, description="Net self-employment income in USD")
    filing_status: str = Field("single", description="Filing status")
    qbi_deduction: bool = Field(True, description="Apply QBI deduction (20%)")

class MultiCountryTaxRequest(BaseModel):
    """Calculate tax for any of 50 countries via rel.tax."""
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    income: float = Field(..., gt=0, description="Annual gross income in local currency")
    extra_params: Optional[dict] = Field(None, description="Country-specific optional parameters")

class IndiaRegimeComparisonRequest(BaseModel):
    """Compare old vs new tax regime for India."""
    gross_income: float = Field(..., gt=0, description="Annual gross income in ₹")

class EffectiveHourlyRateRequest(BaseModel):
    """Calculate effective hourly rate after taxes for any country."""
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO country code")
    annual_income: float = Field(..., gt=0, description="Annual gross income in local currency")
    weekly_hours: int = Field(40, ge=1, le=168, description="Weekly working hours")
    paid_days_off: int = Field(20, ge=0, description="Annual paid days off")

class ExternalTaxCalculationResponse(BaseModel):
    """Generic response wrapper for external tax API calculations."""
    source: str = Field(..., description="API source: fincalculator.in or rel.tax")
    country: str = Field(..., description="Country code")
    data: dict = Field(..., description="Raw API response data")

class IndiaRegimeComparisonResponse(BaseModel):
    """India old vs new regime comparison result."""
    gross_income: float
    old_regime: dict
    new_regime: dict
    savings: float
    recommendation: str

class EffectiveHourlyRateResponse(BaseModel):
    """Post-tax effective hourly rate."""
    country: str
    gross_income: float
    net_income: float
    hourly_rate: float
    daily_rate: float
    working_days: int
    effective_tax_rate: float


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — INVOICE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class InvoiceLineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    amount: float

class InvoiceCreate(BaseModel):
    client_name: str
    client_email: Optional[EmailStr] = None
    client_address: Optional[str] = None
    items: list[InvoiceLineItem]
    tax_rate: float = 0.0
    currency_code: str = "INR"
    issue_date: str  # YYYY-MM-DD
    due_date: str
    notes: Optional[str] = None
    recurring_config: Optional[dict] = None

class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[EmailStr] = None
    client_address: Optional[str] = None
    items: Optional[list[InvoiceLineItem]] = None
    tax_rate: Optional[float] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class InvoiceOut(BaseModel):
    id: uuid.UUID
    invoice_number: str
    client_name: str
    client_email: Optional[str] = None
    client_address: Optional[str] = None
    items_json: Optional[list] = None
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    amount_paid: float
    currency_code: str
    status: str
    issue_date: datetime
    due_date: datetime
    paid_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class InvoicePaymentCreate(BaseModel):
    amount: float
    payment_date: str
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

class InvoicePaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: float
    payment_date: datetime
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class AgingBucket(BaseModel):
    period: str  # "current" | "1-30" | "31-60" | "61-90" | "90+"
    count: int
    total: float
    invoices: list[InvoiceOut] = []

class AgingReport(BaseModel):
    total_outstanding: float
    buckets: list[AgingBucket]


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — EXPENSE APPROVAL WORKFLOWS
# ═══════════════════════════════════════════════════════════════════

class ApprovalPolicyCreate(BaseModel):
    name: str
    min_amount: float = 0
    max_amount: Optional[float] = None
    required_approvers: int = 1
    auto_approve_roles: Optional[list[str]] = None
    categories: Optional[list[str]] = None

class ApprovalPolicyOut(BaseModel):
    id: uuid.UUID
    name: str
    min_amount: float
    max_amount: Optional[float] = None
    required_approvers: int
    auto_approve_roles: Optional[list] = None
    categories: Optional[list] = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class ApprovalDecisionRequest(BaseModel):
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None

class ExpenseApprovalOut(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    policy_id: uuid.UUID
    requested_by: uuid.UUID
    requester_name: Optional[str] = None
    status: str
    approved_by: Optional[uuid.UUID] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — CASH FLOW SCENARIO PLANNING
# ═══════════════════════════════════════════════════════════════════

class ScenarioAssumptions(BaseModel):
    # Core assumptions
    revenue_growth_pct: float = 0.0
    expense_change_pct: float = 0.0
    new_monthly_revenue: float = 0.0
    removed_monthly_expense: float = 0.0
    one_time_income: float = 0.0
    one_time_expense: float = 0.0
    # Extended assumptions
    headcount_change: int = 0
    avg_salary_per_head: float = 0.0
    customer_churn_pct: float = 0.0
    pricing_change_pct: float = 0.0
    tax_rate_pct: float = 0.0
    capex_monthly: float = 0.0
    loan_repayment_monthly: float = 0.0
    seasonal_dip_months: list[int] = []

class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    assumptions: ScenarioAssumptions
    is_baseline: bool = False

class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    assumptions: Optional[ScenarioAssumptions] = None

class ScenarioResultPoint(BaseModel):
    month: str
    projected_income: float
    projected_expenses: float
    net_cash_flow: float
    cumulative_cash: float

class ScenarioOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    assumptions_json: Optional[dict] = None
    result_json: Optional[dict] = None
    is_baseline: bool
    computed_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}

class ScenarioComparisonResponse(BaseModel):
    scenarios: list[ScenarioOut]
    comparison_data: list[dict]

class SensitivityRequest(BaseModel):
    variable_name: str  # e.g. "revenue_growth_pct"
    range_min: float
    range_max: float
    steps: int = 10

class SensitivityResponse(BaseModel):
    variable_name: str
    data_points: list[dict]  # [{value, runway_months, net_cash_flow}]

class MonteCarloRequest(BaseModel):
    num_simulations: int = 1000
    months_ahead: int = 12
    revenue_std: float = 0.10    # income volatility (std dev)
    expense_std: float = 0.08    # expense volatility (std dev)

    def model_post_init(self, __context: object) -> None:
        """Accept frontend field aliases: simulations → num_simulations, months → months_ahead."""
        pass  # Handled by populate_by_name below

    model_config = {"populate_by_name": True}

class MonteCarloResponse(BaseModel):
    num_simulations: int
    months_ahead: int
    p10_runway: float
    p50_runway: float
    p90_runway: float
    p10_cash: float
    p50_cash: float
    p90_cash: float
    distribution: list[dict]
    # Baseline transparency — lets the UI show what inputs drove the simulation
    baseline_monthly_income: float = 0
    baseline_monthly_expense: float = 0
    starting_cash: float = 0


# ── Scenario Templates ────────────────────────────────────────────

class ScenarioTemplate(BaseModel):
    id: str
    name: str
    description: str
    industry: str
    assumptions: ScenarioAssumptions


# ── Scenario Sharing ──────────────────────────────────────────────

class ScenarioShareCreate(BaseModel):
    shared_with_user_id: uuid.UUID
    permission: str = "viewer"  # viewer | editor

class ScenarioShareOut(BaseModel):
    id: uuid.UUID
    scenario_id: uuid.UUID
    shared_by_user_id: uuid.UUID
    shared_with_user_id: uuid.UUID
    permission: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# VENDOR REVIEWS & PERFORMANCE SCORING
# ═══════════════════════════════════════════════════════════════════

class VendorReviewCreate(BaseModel):
    delivery_rating: int  # 1-5
    quality_rating: int  # 1-5
    responsiveness_rating: int  # 1-5
    cost_rating: int  # 1-5
    comment: Optional[str] = None

class VendorReviewOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    delivery_rating: int
    quality_rating: int
    responsiveness_rating: int
    cost_rating: int
    comment: Optional[str] = None
    review_date: datetime
    model_config = {"from_attributes": True}

class VendorScorecard(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str
    total_reviews: int
    avg_delivery: float
    avg_quality: float
    avg_responsiveness: float
    avg_cost: float
    composite_score: float  # 0-5 weighted avg


# ═══════════════════════════════════════════════════════════════════
# VENDOR CONTRACT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class ContractCreate(BaseModel):
    title: str
    contract_type: str  # service, license, lease, subscription, maintenance
    start_date: datetime
    end_date: datetime
    value: Optional[float] = None
    auto_renew: bool = False
    renewal_notice_days: int = 30
    notes: Optional[str] = None

class ContractUpdate(BaseModel):
    title: Optional[str] = None
    contract_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    value: Optional[float] = None
    auto_renew: Optional[bool] = None
    renewal_notice_days: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class ContractOut(BaseModel):
    id: uuid.UUID
    vendor_id: uuid.UUID
    title: str
    contract_type: str
    start_date: datetime
    end_date: datetime
    value: Optional[float] = None
    auto_renew: bool
    renewal_notice_days: int
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ContractExpiringSoon(BaseModel):
    contract: ContractOut
    vendor_name: str
    days_remaining: int
