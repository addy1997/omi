import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into os.environ so all downstream os.getenv() calls see the values
load_dotenv(override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OMI_", env_file=".env", extra="ignore")

    # LLM models
    supervisor_model: str = "anthropic/claude-sonnet-4-5"
    coder_model: str = "anthropic/claude-sonnet-4-5"
    explorer_model: str = "anthropic/claude-haiku-4-5"
    planner_model: str = "anthropic/claude-sonnet-4-5"
    researcher_model: str = "anthropic/claude-haiku-4-5"
    triager_model: str = "anthropic/claude-haiku-4-5"

    # Filesystem
    repos_dir: Path = Path("/tmp/omi/repos")
    worktrees_dir: Path = Path("/tmp/omi/worktrees")

    # Storage
    db_url: str = "sqlite+aiosqlite:///./omi.db"

    # Sandbox
    sandbox: str = "subprocess"
    shell_timeout: int = 120

    # API
    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = "change-me"

    # GitHub — read directly from env (no OMI_ prefix needed)
    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def github_owner(self) -> str:
        return os.getenv("GITHUB_OWNER", "")

    def ensure_dirs(self) -> None:
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
