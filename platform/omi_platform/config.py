from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLATFORM_", env_file=".env", extra="ignore")

    # API
    host: str = "0.0.0.0"
    port: int = 9000          # platform runs on 9000; agents on their own ports
    secret_key: str = "change-me-in-production"

    # Storage
    db_url: str = "sqlite+aiosqlite:///./platform.db"

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24   # 1 day

    # Agent health
    heartbeat_interval_s: int = 30      # how often agents must ping
    heartbeat_timeout_s: int = 90       # mark offline after this

    # Routing LLM (used to auto-route ambiguous tasks)
    router_model: str = "anthropic/claude-haiku-4-5"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Dashboard
    dashboard_url: str = "http://localhost:5173"


settings = Settings()
