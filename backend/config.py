from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database (Neon) ──
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/aicfo?sslmode=require"

    # ── Redis (Upstash) ──
    REDIS_URL: str = "rediss://default:xxx@xxx.upstash.io:6379"
    CACHE_TTL_SECONDS: int = 300  # 5 min default

    # ── Clerk Auth ──
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_JWKS_URL: str = "https://api.clerk.com/v1/jwks"
    CLERK_ISSUER: str = ""  # e.g. https://your-app.clerk.accounts.dev

    # ── OpenAI ──
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Encryption (field-level for webhooks, API keys) ──
    WEBHOOK_ENCRYPTION_KEY: str = ""  # Fernet key — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # ── Observability (OpenTelemetry) ──
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "ai-cfo-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"  # gRPC

    # ── Plaid (ADVANCE-003) ──
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"  # sandbox | development | production
    PLAID_WEBHOOK_URL: str = ""  # e.g. https://yourdomain.com/api/plaid/webhook

    # ── Embeddings (ADVANCE-005) ──
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # free, local, 384 dims
    EMBEDDING_DIMENSIONS: int = 384

    # ── App ──
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
