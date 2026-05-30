"""Agent SDK — every agent on the platform implements this interface.

Pattern:
  1. Subclass AgentBase in your agent project.
  2. Fill in metadata (name, description, capabilities, version).
  3. Implement handle(task) → TaskResult.
  4. Call agent.register(platform_url, api_key) on startup.
  5. Serve AgentServer.app() — the platform will call your /run endpoint.

Omi does this in omi/platform_adapter.py.
"""
from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    ONLINE  = "online"
    OFFLINE = "offline"
    BUSY    = "busy"
    ERROR   = "error"


class Capability(str, Enum):
    """Well-known capability tags agents can advertise."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW     = "code_review"
    CODE_SEARCH     = "code_search"
    PLANNING        = "planning"
    ISSUE_TRIAGE    = "issue_triage"
    WEB_RESEARCH    = "web_research"
    DATA_ANALYSIS   = "data_analysis"
    DEVOPS          = "devops"
    DOCUMENTATION   = "documentation"
    TESTING         = "testing"
    GENERAL         = "general"


# ── Task & Result models ──────────────────────────────────────

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str | None = None          # None = platform auto-routes
    context: dict[str, Any] = {}
    parent_task_id: str | None = None    # for multi-agent chains
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = {}


class TaskResult(BaseModel):
    task_id: str
    agent_id: str
    status: TaskStatus = TaskStatus.COMPLETED
    content: str
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: str | None = None
    artifacts: dict[str, Any] = {}      # files, PRs, issues created, etc.
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentInfo(BaseModel):
    """Registration record sent to the platform."""
    id: str
    name: str
    description: str
    capabilities: list[str]
    version: str = "0.1.0"
    base_url: str                        # http://host:port — platform calls /run, /health
    api_key: str = ""                    # agent's own API key for secured endpoints
    status: AgentStatus = AgentStatus.ONLINE
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = {}


# ── AgentBase ─────────────────────────────────────────────────

class AgentBase(ABC):
    """Base class for all Omi platform agents."""

    # Subclasses set these as class attributes
    name: str = "unnamed-agent"
    description: str = ""
    capabilities: list[str] = [Capability.GENERAL]
    version: str = "0.1.0"

    def __init__(self, agent_id: str | None = None, base_url: str = ""):
        self.agent_id = agent_id or f"{self.name}-{str(uuid.uuid4())[:8]}"
        self.base_url = base_url
        self._platform_url: str | None = None
        self._platform_api_key: str | None = None

    @abstractmethod
    async def handle(self, task: Task) -> TaskResult:
        """Process a task and return a result. Must be implemented by every agent."""

    async def health_check(self) -> bool:
        """Override to add custom health logic."""
        return True

    def agent_info(self) -> AgentInfo:
        return AgentInfo(
            id=self.agent_id,
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            version=self.version,
            base_url=self.base_url,
        )

    # ── Platform integration ──────────────────────────────────

    async def register(self, platform_url: str, platform_api_key: str = "") -> bool:
        """Register this agent with the platform. Call on startup."""
        self._platform_url = platform_url.rstrip("/")
        self._platform_api_key = platform_api_key
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._platform_url}/agents/register",
                    json=self.agent_info().model_dump(mode="json"),
                    headers={"X-API-Key": platform_api_key} if platform_api_key else {},
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            print(f"[{self.name}] Registration failed: {e}")
            return False

    async def deregister(self) -> bool:
        """Remove this agent from the platform registry."""
        if not self._platform_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.delete(
                    f"{self._platform_url}/agents/{self.agent_id}",
                    headers={"X-API-Key": self._platform_api_key or ""},
                )
                return resp.status_code in (200, 204)
        except Exception:
            return False

    async def send_heartbeat(self) -> None:
        """Send a heartbeat to the platform. Called by AgentServer automatically."""
        if not self._platform_url:
            return
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"{self._platform_url}/agents/{self.agent_id}/heartbeat",
                    headers={"X-API-Key": self._platform_api_key or ""},
                )
        except Exception:
            pass

    async def start_heartbeat_loop(self, interval_s: int = 30) -> None:
        while True:
            await asyncio.sleep(interval_s)
            await self.send_heartbeat()


# ── AgentServer ───────────────────────────────────────────────

def make_agent_server(agent: AgentBase):
    """Return a FastAPI app that exposes the standard agent API.

    The platform calls:
      POST /run      → agent.handle(task)
      GET  /health   → agent.health_check()
      GET  /info     → agent.agent_info()
    """
    import time
    from fastapi import FastAPI, HTTPException

    app = FastAPI(title=agent.name, version=agent.version)

    @app.get("/health")
    async def health():
        ok = await agent.health_check()
        return {"status": "ok" if ok else "degraded", "agent": agent.name}

    @app.get("/info")
    async def info():
        return agent.agent_info().model_dump()

    @app.post("/run", response_model=TaskResult)
    async def run(task: Task):
        t0 = time.monotonic()
        try:
            result = await agent.handle(task)
            result.duration_ms = int((time.monotonic() - t0) * 1000)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app
