from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERA_", env_file=".env", extra="ignore")

    # LLM
    supervisor_model: str = "ollama/llama3.2"
    planner_model: str = "ollama/llama3.2"

    # Storage
    db_url: str = "sqlite+aiosqlite:///./vera.db"

    # Testing defaults
    test_framework: str = "pytest"
    coverage_threshold: float = 80.0
    test_timeout_s: int = 120


settings = Settings()
