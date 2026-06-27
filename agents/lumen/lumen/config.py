from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LUMEN_", env_file=".env", extra="ignore")

    # LLM
    supervisor_model: str = "ollama/llama3.2"
    planner_model: str = "ollama/llama3.2"

    # Storage
    db_url: str = "sqlite+aiosqlite:///./lumen.db"

    # Documentation defaults
    docstring_style: str = "google"   # google | numpy | sphinx
    doc_coverage_threshold: float = 80.0


settings = Settings()
