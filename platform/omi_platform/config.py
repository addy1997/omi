from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATFORM_", env_file=".env", extra="ignore")

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 9000
    environment: str = "development"  # development, staging, production
    debug: bool = False  # ⚠️ Disable in production

    # ── Security ─────────────────────────────────────────────
    secret_key: str = "change-me-in-production"  # 🔐 Change in production!
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24   # 1 day

    # ── Storage ──────────────────────────────────────────────
    db_url: str = "sqlite+aiosqlite:///./platform.db"

    # ── Agent Health ─────────────────────────────────────────
    heartbeat_interval_s: int = 30      # how often agents must ping
    heartbeat_timeout_s: int = 90       # mark offline after this

    # ── Routing LLM (for task routing) ───────────────────────
    router_model: str = "anthropic/claude-haiku-4-5"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # ── Dashboard (for CORS) ─────────────────────────────────
    dashboard_url: str = "http://localhost:5173"

    # ── Sandbox (shell execution) ────────────────────────────
    sandbox: str = "docker"  # docker (secure) or subprocess (fast)

    # ── Logging ──────────────────────────────────────────────
    log_level: str = "INFO"
    enable_logging: bool = True


settings = Settings()
