import ssl as _ssl
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields in .env file
    )
    
    # ── Database ──
    # L-003: Generic local default — override via .env for Neon / hosted Postgres
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aicfo"

    # ── Redis ──
    # L-003: Generic local default — override via .env for Upstash / hosted Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300  # 5 min default

    # ── Clerk Auth ──
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_JWKS_URL: str = "https://api.clerk.com/v1/jwks"
    CLERK_ISSUER: str = ""  # e.g. https://your-app.clerk.accounts.dev

    # ── OpenAI ──
    # SEC-FIX: Must be set in production for AI chat to work
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Encryption (field-level for webhooks, API keys) ──
    # SEC-FIX: Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    WEBHOOK_ENCRYPTION_KEY: str = ""  # Fernet key — REQUIRED in production
    # CRIT-004: Per-deployment KDF salt — REQUIRED when using PBKDF2 fallback
    # Generate with: python -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
    KEY_DERIVATION_SALT: str = ""

    # ── Observability (OpenTelemetry) ──
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "ai-cfo-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"  # gRPC
    OTEL_INSECURE: bool = False  # HIGH-009: Default to secure (TLS) connections

    # ── Plaid (ADVANCE-003) ──
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"  # sandbox | development | production
    PLAID_WEBHOOK_URL: str = ""  # e.g. https://yourdomain.com/api/plaid/webhook

    # ── Embeddings (ADVANCE-005) ──
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # free, local, 384 dims
    EMBEDDING_DIMENSIONS: int = 384

    # ── File Uploads (FILE-001) ──
    UPLOAD_DIR: str = "./uploads"        # local storage root
    MAX_UPLOAD_SIZE_MB: int = 10         # max file size in MB

    # ── Email Configuration ──
    EMAIL_PROVIDER: str = "smtp"  # sendgrid | aws_ses | smtp
    SENDGRID_API_KEY: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    EMAIL_FROM_ADDRESS: str = "noreply@example.com"
    EMAIL_FROM_NAME: str = "AI CFO Platform"

    # ── Slack Configuration ──
    SLACK_WEBHOOK_URL: str | None = None
    SLACK_BOT_TOKEN: str | None = None
    SLACK_ENABLED: bool = False
    SLACK_DEFAULT_CHANNEL: str = "#general"
    SLACK_SIGNING_SECRET: str | None = None
    APP_BASE_URL: str = "http://localhost:3000"

    # ── App ──
    # SEC-FIX: CRITICAL - Must override CORS_ORIGINS in production!
    # Default to permissive dev origins — MUST override in production
    # Set via env: CORS_ORIGINS='["https://app.yourdomain.com"]'
    # WARNING: Leaving localhost origins in production will break the frontend
    # CONFIG-001: Startup check will warn if localhost origins in production
    CORS_ORIGINS: str = '["http://localhost:3000", "http://localhost:3001"]'
    DEBUG: bool = False
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS from JSON string to list."""
        import json
        if isinstance(self.CORS_ORIGINS, str):
            try:
                return json.loads(self.CORS_ORIGINS)
            except json.JSONDecodeError:
                # Fallback to default if parsing fails
                return ["http://localhost:3000", "http://localhost:3001"]
        return self.CORS_ORIGINS

    # ── Forecast model (L-004) ──
    # "linear" = LinearForecastService (default, zero extra deps)
    # "prophet" = ProphetForecastService (requires `pip install prophet`)
    FORECAST_MODEL: str = "linear"

    # ── Password Policy Framework (COMPLIANCE-003) ──
    # Configurable password policy for future custom authentication implementations
    # Note: Current Clerk authentication does not use these settings
    PASSWORD_POLICY_ENABLED: bool = False  # Enable for custom auth implementations
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 128
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL_CHARS: bool = True
    PASSWORD_SPECIAL_CHARS: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    PASSWORD_MIN_SPECIAL_CHARS: int = 1
    PASSWORD_PREVENT_COMMON_PASSWORDS: bool = True
    PASSWORD_PREVENT_USER_INFO: bool = True  # Prevent passwords containing user info
    PASSWORD_HISTORY_COUNT: int = 5  # Number of previous passwords to remember
    PASSWORD_EXPIRY_DAYS: int = 90  # Password expiration in days (0 = no expiry)

    # ── GDPR/CCPA Compliance Framework (COMPLIANCE-004) ──
    # Data protection and privacy compliance settings
    COMPLIANCE_ENABLED: bool = True  # Enable GDPR/CCPA compliance features
    DATA_EXPORT_ENABLED: bool = True  # Enable data export (GDPR Article 20)
    DATA_DELETION_ENABLED: bool = True  # Enable data deletion (GDPR Article 17)
    CONSENT_MANAGEMENT_ENABLED: bool = True  # Enable consent tracking and management
    DATA_RETENTION_ENABLED: bool = True  # Enable automated data retention policies
    
    # Data retention policies (in days)
    DEFAULT_DATA_RETENTION_DAYS: int = 2555  # ~7 years (financial records)
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # ~7 years (compliance requirement)
    CHAT_MESSAGE_RETENTION_DAYS: int = 365  # 1 year
    FILE_UPLOAD_RETENTION_DAYS: int = 1095  # 3 years
    INACTIVE_USER_RETENTION_DAYS: int = 1095  # 3 years after last login
    
    # Consent management settings
    CONSENT_COOKIE_NAME: str = "ai_cfo_consent"
    CONSENT_COOKIE_DURATION_DAYS: int = 365  # 1 year
    REQUIRE_EXPLICIT_CONSENT: bool = True  # Require explicit consent for data processing
    
    # Data export settings
    EXPORT_FORMAT: str = "json"  # json | csv (json is more comprehensive)
    EXPORT_INCLUDE_METADATA: bool = True  # Include creation dates, IDs, etc.
    EXPORT_MAX_FILE_SIZE_MB: int = 100  # Maximum export file size
    
    # Data deletion settings
    DELETION_VERIFICATION_REQUIRED: bool = True  # Require email verification for deletion
    DELETION_GRACE_PERIOD_DAYS: int = 30  # Grace period before permanent deletion
    SOFT_DELETE_ENABLED: bool = True  # Use soft delete initially, then hard delete after grace period

    # ── EXT-004: Neon URL transformation ──────────────────────────
    # asyncpg does not accept ?sslmode=require in the DSN.
    # These properties isolate the workaround so database.py stays clean.
    # Reference: https://neon.tech/docs/connect/connectivity-issues

    @property
    def database_url_for_asyncpg(self) -> str:
        """Return DATABASE_URL with sslmode stripped from query string."""
        parsed = urlparse(self.DATABASE_URL)
        params = parse_qs(parsed.query)
        params.pop("sslmode", None)
        clean_query = urlencode({k: v[0] for k, v in params.items()}) if params else ""
        return urlunparse(parsed._replace(query=clean_query))

    @property
    def database_connect_args(self) -> dict:
        """Return SSL connect_args if the original DSN had sslmode=require."""
        parsed = urlparse(self.DATABASE_URL)
        params = parse_qs(parsed.query)
        sslmode = params.get("sslmode", [None])[0]
        if sslmode in ("require", "verify-full", "verify-ca"):
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            return {"ssl": ctx}
        return {}


settings = Settings()
