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

    # ── App ──
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
