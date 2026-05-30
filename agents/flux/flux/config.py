from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(override=False)

class Settings(BaseSettings):
    # LLM
    supervisor_model: str = "anthropic/claude-sonnet-4-5"
    analyst_model: str = "anthropic/claude-haiku-4-5"

    # Storage
    db_url: str = "sqlite+aiosqlite:///./flux.db"
    duckdb_path: str = "./data.duckdb"

    # Data connections
    postgres_url: str = "postgresql://user:pass@localhost:5432/analytics"

    # Visualization
    plotly_enabled: bool = True

settings = Settings()
