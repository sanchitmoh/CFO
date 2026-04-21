"""
AI CFO — SQLAlchemy ORM Models
13 indexed tables, multi-tenant via workspace_id, financial-grade precision.
"""
import uuid
import enum
from decimal import Decimal
from datetime import datetime

from sqlalchemy import (
    String, Float, DateTime, Boolean, SmallInteger,
    Text, ForeignKey, Numeric, Index, CheckConstraint, Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
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
    horizon_months: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="v1_linear"
    )
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="forecast_results")


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
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="audit_logs")
    user: Mapped["User"] = relationship(back_populates="audit_logs")


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
        DateTime(timezone=True), default=datetime.utcnow
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
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    user: Mapped["User"] = relationship("User")

