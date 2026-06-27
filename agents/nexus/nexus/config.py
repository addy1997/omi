from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=False)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXUS_", env_file=".env", extra="ignore")

    # LLM
    supervisor_model: str = "ollama/llama3.2"
    planner_model: str = "ollama/llama3.2"

    # Storage
    db_url: str = "sqlite+aiosqlite:///./nexus.db"

    # Cloud providers
    aws_region: str = "us-east-1"
    k8s_namespace: str = "default"

    # Monitoring
    prometheus_url: str = "http://localhost:9090"
    grafana_url: str = "http://localhost:3000"

settings = Settings()
