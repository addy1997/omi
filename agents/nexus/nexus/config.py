from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(override=False)

class Settings(BaseSettings):
    # LLM
    supervisor_model: str = "anthropic/claude-sonnet-4-5"
    planner_model: str = "anthropic/claude-sonnet-4-5"

    # Storage
    db_url: str = "sqlite+aiosqlite:///./nexus.db"

    # Cloud providers
    aws_region: str = "us-east-1"
    k8s_namespace: str = "default"

    # Monitoring
    prometheus_url: str = "http://localhost:9090"
    grafana_url: str = "http://localhost:3000"

settings = Settings()
