"""
AI CFO — SQLAlchemy ORM Models
13 indexed tables, multi-tenant via workspace_id, financial-grade precision.
"""
import uuid
import enum
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, DateTime, Boolean, SmallInteger,
    Text, ForeignKey, Numeric, Index, CheckConstraint, Enum as SAEnum,
    LargeBinary,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

try:
    from pgvector.sqlalchemy import Vector as _Vector
    _VECTOR_TYPE = _Vector(384)
except ImportError:
    _VECTOR_TYPE = LargeBinary  # fallback — won't support similarity ops

from database import Base


# ═══════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════

class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    cfo = "cfo"
    accountant = "accountant"
    investor = "investor"
    employee = "employee"


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class GoalStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class TaxDeductibility(str, enum.Enum):
    deductible = "deductible"
    partially_deductible = "partially_deductible"
    non_deductible = "non_deductible"
    exempt = "exempt"


class TaxEstimateStatus(str, enum.Enum):
    draft = "draft"
    filed = "filed"
    paid = "paid"


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"
    partially_paid = "partially_paid"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    auto_approved = "auto_approved"


class ContractType(str, enum.Enum):
    service = "service"
    license = "license"
    lease = "lease"
    subscription = "subscription"
    maintenance = "maintenance"


class ContractStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    terminated = "terminated"
    pending_renewal = "pending_renewal"


class SharePermission(str, enum.Enum):
    viewer = "viewer"
    editor = "editor"


# ═══════════════════════════════════════════════════════════════════
# WORKSPACE — Multi-tenant container
# ═══════════════════════════════════════════════════════════════════

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general_smb", index=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    fiscal_year_start: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="workspace")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="workspace")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="workspace")
    goals: Mapped[list["Goal"]] = relationship(back_populates="workspace")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="workspace")
    alert_rules: Mapped[list["AlertRule"]] = relationship(back_populates="workspace")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="workspace")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="workspace")
    forecast_results: Mapped[list["ForecastResult"]] = relationship(back_populates="workspace")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="workspace")
    # Phase 2
    vendors: Mapped[list["Vendor"]] = relationship(back_populates="workspace")
    tax_categories: Mapped[list["TaxCategory"]] = relationship(back_populates="workspace")
    tax_estimates: Mapped[list["TaxEstimate"]] = relationship(back_populates="workspace")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="workspace")
    approval_policies: Mapped[list["ApprovalPolicy"]] = relationship(back_populates="workspace")
    scenarios: Mapped[list["Scenario"]] = relationship(back_populates="workspace")


# ═══════════════════════════════════════════════════════════════════
# USER — Enhanced with Clerk + workspace
# ═══════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email_ws", "email", "workspace_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clerk_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.owner)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="users")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="user")
    goals: Mapped[list["Goal"]] = relationship(back_populates="user")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="user")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


# ═══════════════════════════════════════════════════════════════════
# TRANSACTION — Financial-grade with composite indexes
# ═══════════════════════════════════════════════════════════════════

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_txn_ws_date", "workspace_id", "date"),
        Index("idx_txn_ws_cat_date", "workspace_id", "category", "date"),
        Index("idx_txn_ws_type", "workspace_id", "type"),
        Index("idx_txn_ws_type_cat_date", "workspace_id", "type", "category", "date"),
        CheckConstraint("amount >= 0", name="ck_txn_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    amount_original: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType), nullable=False)
    account: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Main Account"
    )
    vendor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )  # manual | csv | api
    # pgvector embedding for semantic search (ADVANCE-005)
    # Column created by migration 002_add_pgvector — 384 dims for all-MiniLM-L6-v2
    description_vec = Column(_VECTOR_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="transactions")
    user: Mapped["User"] = relationship(back_populates="transactions")


# ═══════════════════════════════════════════════════════════════════
# BUDGET — Monthly category budgets
# ═══════════════════════════════════════════════════════════════════

class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        Index("idx_budget_ws_cat_month", "workspace_id", "category", "month", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    alert_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    current_spend: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0.0
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="budgets")
    user: Mapped["User"] = relationship(back_populates="budgets")


# ═══════════════════════════════════════════════════════════════════
# GOAL — Financial targets (Feature 5)
# ═══════════════════════════════════════════════════════════════════

class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("idx_goals_ws_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0.0)
    metric_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # revenue | savings | expense_reduction
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[GoalStatus] = mapped_column(SAEnum(GoalStatus), default=GoalStatus.active)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="goals")
    user: Mapped["User"] = relationship(back_populates="goals")


# ═══════════════════════════════════════════════════════════════════
# ALERT — Enhanced with severity enum + actions
# ═══════════════════════════════════════════════════════════════════

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alerts_ws_unread", "workspace_id", "is_read", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), default=AlertSeverity.info)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    action_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="alerts")
    user: Mapped["User"] = relationship(back_populates="alerts")


# ═══════════════════════════════════════════════════════════════════
# ALERT RULES — User-configurable triggers
# ═══════════════════════════════════════════════════════════════════

class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("idx_alert_rules_ws_enabled", "workspace_id", "is_enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # low_cash | short_runway | overspend | revenue_drop
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_slack: Mapped[bool] = mapped_column(Boolean, default=False)
    slack_webhook: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="alert_rules")


# ═══════════════════════════════════════════════════════════════════
# CHAT SESSION — Owns a sequence of chat messages (SCHEMA-003)
# ═══════════════════════════════════════════════════════════════════

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_sessions_ws_user", "workspace_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="chat_sessions")
    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


# ═══════════════════════════════════════════════════════════════════
# CHAT MESSAGES — Enhanced with RAG metadata
# ═══════════════════════════════════════════════════════════════════

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_msg_session", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # high | medium | low
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="chat_messages")
    user: Mapped["User"] = relationship(back_populates="chat_messages")
    session: Mapped["ChatSession"] = relationship(back_populates="messages")


# ═══════════════════════════════════════════════════════════════════
# FORECAST RESULTS — Cache expensive ML computations
# ═══════════════════════════════════════════════════════════════════

class ForecastResult(Base):
    __tablename__ = "forecast_results"
    __table_args__ = (
        Index("idx_forecast_ws_scenario", "workspace_id", "scenario"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    scenario: Mapped[str] = mapped_column(String(20), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    horizon_months: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="v1_linear"
    )
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="forecast_results")


# ═══════════════════════════════════════════════════════════════════
# EXCHANGE RATES — Currency Conversion Metadata
# ═══════════════════════════════════════════════════════════════════

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        Index("idx_exchange_rate_base_target_date", "base_currency", "target_currency", "date", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
# ═══════════════════════════════════════════════════════════════════
# AUDIT LOG — Change tracking (Feature D)
# ═══════════════════════════════════════════════════════════════════

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_ws_time", "workspace_id", "created_at"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # budget.create | forecast.run | alert.dismiss | ...
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # budget | transaction | alert | report | forecast
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # NOTE: ip_address intentionally removed — PII under GDPR/CCPA
    # without consent mechanism, retention policy, or deletion capability.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="audit_logs")
    user: Mapped["User"] = relationship(back_populates="audit_logs")


# ═══════════════════════════════════════════════════════════════════
# FILE UPLOAD — Audit trail for CSV imports (FILE-001)
# ═══════════════════════════════════════════════════════════════════

class FileUploadStatus(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    failed = "failed"
    duplicate = "duplicate"


class FileUpload(Base):
    __tablename__ = "file_uploads"
    __table_args__ = (
        Index("idx_file_upload_ws_hash", "workspace_id", "content_hash"),
        Index("idx_file_upload_ws_created", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)  # bytes
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 hex digest
    storage_path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # local path or S3 key
    row_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[FileUploadStatus] = mapped_column(
        SAEnum(FileUploadStatus), default=FileUploadStatus.pending
    )
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")


# ═══════════════════════════════════════════════════════════════════
# INDUSTRY BENCHMARKS — Static reference data (Feature C)
# ═══════════════════════════════════════════════════════════════════

class IndustryBenchmark(Base):
    __tablename__ = "industry_benchmarks"
    __table_args__ = (
        Index(
            "idx_benchmark_unique", "industry", "metric_name", "year",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    industry: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="percentage")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2025)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ═══════════════════════════════════════════════════════════════════
# PLAID ITEM — Banking connections (ADVANCE-003)
# ═══════════════════════════════════════════════════════════════════

class PlaidItem(Base):
    __tablename__ = "plaid_items"
    __table_args__ = (
        Index("idx_plaid_ws_item", "workspace_id", "item_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Fernet-encrypted access token
    institution_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Plaid sync cursor for incremental updates
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")


# ═══════════════════════════════════════════════════════════════════
# GDPR/CCPA COMPLIANCE — Data protection and privacy (COMPLIANCE-004)
# ═══════════════════════════════════════════════════════════════════

class ConsentStatus(str, enum.Enum):
    granted = "granted"
    withdrawn = "withdrawn"
    pending = "pending"


class DataExportStatus(str, enum.Enum):
    requested = "requested"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    expired = "expired"


class DataDeletionStatus(str, enum.Enum):
    requested = "requested"
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class UserConsent(Base):
    """Track user consent for data processing under GDPR/CCPA."""
    __tablename__ = "user_consents"
    __table_args__ = (
        Index("idx_consent_user_type", "user_id", "consent_type"),
        Index("idx_consent_ws_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    consent_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # data_processing | analytics | marketing | third_party_sharing
    status: Mapped[ConsentStatus] = mapped_column(SAEnum(ConsentStatus), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hash of IP for audit trail
    user_agent_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 hash of user agent
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")


class DataExport(Base):
    """Track GDPR Article 20 data export requests."""
    __tablename__ = "data_exports"
    __table_args__ = (
        Index("idx_export_user_status", "user_id", "status"),
        Index("idx_export_ws_created", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[DataExportStatus] = mapped_column(SAEnum(DataExportStatus), nullable=False)
    format: Mapped[str] = mapped_column(
        String(10), nullable=False, default="json"
    )  # json | csv
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    include_metadata: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # Export files expire after 30 days
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")


class DataDeletion(Base):
    """Track GDPR Article 17 data deletion requests."""
    __tablename__ = "data_deletions"
    __table_args__ = (
        Index("idx_deletion_user_status", "user_id", "status"),
        Index("idx_deletion_scheduled", "scheduled_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[DataDeletionStatus] = mapped_column(SAEnum(DataDeletionStatus), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_records_count: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")


class RetentionPolicy(Base):
    """Define data retention policies for automated cleanup."""
    __tablename__ = "retention_policies"
    __table_args__ = (
        Index("idx_retention_ws_entity", "workspace_id", "entity_type", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # transactions | audit_logs | chat_messages | file_uploads | users
    retention_days: Mapped[int] = mapped_column(nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_cleanup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_cleanup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cleanup_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — VENDOR MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (
        Index("idx_vendor_ws_name", "workspace_id", "name"),
        Index("idx_vendor_ws_active", "workspace_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(nullable=False, default=30)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="vendors")
    contacts: Mapped[list["VendorContact"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )


class VendorContact(Base):
    __tablename__ = "vendor_contacts"
    __table_args__ = (Index("idx_vc_vendor", "vendor_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    vendor: Mapped["Vendor"] = relationship(back_populates="contacts")


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — TAX MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class TaxCategory(Base):
    __tablename__ = "tax_categories"
    __table_args__ = (
        Index("idx_taxcat_ws_category", "workspace_id", "category", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    tax_code: Mapped[TaxDeductibility] = mapped_column(
        SAEnum(TaxDeductibility), nullable=False, default=TaxDeductibility.non_deductible
    )
    deduction_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False, default="IN")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="tax_categories")


class TaxEstimate(Base):
    __tablename__ = "tax_estimates"
    __table_args__ = (
        Index("idx_taxest_ws_quarter", "workspace_id", "quarter"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False, default="IN")
    taxable_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    estimated_tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    effective_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    deductions_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    status: Mapped[TaxEstimateStatus] = mapped_column(
        SAEnum(TaxEstimateStatus), nullable=False, default=TaxEstimateStatus.draft
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="tax_estimates")


class TaxJurisdiction(Base):
    __tablename__ = "tax_jurisdictions"
    __table_args__ = (
        Index("idx_taxjur_ws_code", "workspace_id", "code", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    tax_rates_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    filing_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="quarterly")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — INVOICE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("idx_inv_ws_status", "workspace_id", "status"),
        Index("idx_inv_ws_client", "workspace_id", "client_name"),
        Index("idx_inv_ws_number", "workspace_id", "invoice_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    items_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.draft
    )
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurring_config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="invoices")
    user: Mapped["User"] = relationship("User")
    payments: Mapped[list["InvoicePayment"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoicePayment(Base):
    __tablename__ = "invoice_payments"
    __table_args__ = (Index("idx_invpay_invoice", "invoice_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    invoice: Mapped["Invoice"] = relationship(back_populates="payments")


class InvoiceSequence(Base):
    """Workspace-scoped sequential invoice numbering."""
    __tablename__ = "invoice_sequences"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    next_number: Mapped[int] = mapped_column(nullable=False, default=1)


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — EXPENSE APPROVAL WORKFLOWS
# ═══════════════════════════════════════════════════════════════════

class ApprovalPolicy(Base):
    __tablename__ = "approval_policies"
    __table_args__ = (Index("idx_ap_ws_active", "workspace_id", "is_active"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    required_approvers: Mapped[int] = mapped_column(nullable=False, default=1)
    auto_approve_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="approval_policies")


class ExpenseApproval(Base):
    __tablename__ = "expense_approvals"
    __table_args__ = (
        Index("idx_ea_ws_status", "workspace_id", "status"),
        Index("idx_ea_ws_requester", "workspace_id", "requested_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("approval_policies.id"), nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.pending
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship("Workspace")
    transaction: Mapped["Transaction"] = relationship("Transaction")
    policy: Mapped["ApprovalPolicy"] = relationship("ApprovalPolicy")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — CASH FLOW SCENARIO PLANNING
# ═══════════════════════════════════════════════════════════════════

class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (Index("idx_scen_ws", "workspace_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assumptions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="scenarios")
    user: Mapped["User"] = relationship("User")
    sensitivity_analyses: Mapped[list["SensitivityAnalysis"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )


class SensitivityAnalysis(Base):
    __tablename__ = "sensitivity_analyses"
    __table_args__ = (Index("idx_sa_scenario", "scenario_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    variable_name: Mapped[str] = mapped_column(String(100), nullable=False)
    range_min: Mapped[float] = mapped_column(Float, nullable=False)
    range_max: Mapped[float] = mapped_column(Float, nullable=False)
    steps: Mapped[int] = mapped_column(nullable=False, default=10)
    results_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    scenario: Mapped["Scenario"] = relationship(back_populates="sensitivity_analyses")


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — SCENARIO SHARING
# ═══════════════════════════════════════════════════════════════════

class ScenarioShare(Base):
    __tablename__ = "scenario_shares"
    __table_args__ = (
        Index("idx_ss_scenario", "scenario_id"),
        Index("idx_ss_user", "shared_with_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    shared_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    permission: Mapped[str] = mapped_column(
        SAEnum(SharePermission, name="share_permission_enum", create_constraint=False),
        default=SharePermission.viewer,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    scenario: Mapped["Scenario"] = relationship("Scenario")


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — VENDOR REVIEWS & PERFORMANCE SCORING
# ═══════════════════════════════════════════════════════════════════

class VendorReview(Base):
    __tablename__ = "vendor_reviews"
    __table_args__ = (
        Index("idx_vr_vendor", "vendor_id"),
        Index("idx_vr_ws", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    delivery_rating: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 1-5
    quality_rating: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 1-5
    responsiveness_rating: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 1-5
    cost_rating: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    vendor: Mapped["Vendor"] = relationship("Vendor")


# ═══════════════════════════════════════════════════════════════════
# PHASE 2 — VENDOR CONTRACT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class VendorContract(Base):
    __tablename__ = "vendor_contracts"
    __table_args__ = (
        Index("idx_vc_vendor_id", "vendor_id"),
        Index("idx_vc_ws", "workspace_id"),
        Index("idx_vc_end_date", "end_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_type: Mapped[str] = mapped_column(
        SAEnum(ContractType, name="contract_type_enum", create_constraint=False),
        nullable=False,
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    renewal_notice_days: Mapped[int] = mapped_column(nullable=False, default=30)
    status: Mapped[str] = mapped_column(
        SAEnum(ContractStatus, name="contract_status_enum", create_constraint=False),
        default=ContractStatus.active,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    vendor: Mapped["Vendor"] = relationship("Vendor")

