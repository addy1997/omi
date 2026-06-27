from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=False)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLUX_", env_file=".env", extra="ignore")

    # LLM
    supervisor_model: str = "ollama/llama3.2"
    analyst_model: str = "ollama/llama3.2"

    # Storage
    db_url: str = "sqlite+aiosqlite:///./flux.db"
    duckdb_path: str = "./data.duckdb"

    # Data connections
    postgres_url: str = "postgresql://user:pass@localhost:5432/analytics"

    # Visualization
    plotly_enabled: bool = True

settings = Settings()
