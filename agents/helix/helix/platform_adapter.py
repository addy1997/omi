"""Omi's platform adapter — registers Omi as an agent on the platform.

Run standalone:   omi serve              (port 8000, no platform needed)
Run with platform: PLATFORM_URL=http://localhost:9000 omi serve-agent

The platform calls POST /run → HelixAgent.handle() → Omi's LangGraph supervisor.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager

import uvicorn

from omi_platform.sdk.agent_base import (  # type: ignore
    AgentBase, Capability, Task, TaskResult, TaskStatus, make_agent_server,
)

from .config import settings
from .memory.session import init_db
from .supervisor.graph import run as omi_run


class HelixAgent(AgentBase):
    name        = "helix"
    description = (
        "Omi — coding agent. Writes, tests, and commits code; reviews PRs; "
        "plans features as GitHub issues; triages issue backlogs; searches the web."
    )
    capabilities = [
        Capability.CODE_GENERATION,
        Capability.CODE_REVIEW,
        Capability.CODE_SEARCH,
        Capability.PLANNING,
        Capability.ISSUE_TRIAGE,
        Capability.WEB_RESEARCH,
        Capability.TESTING,
    ]
    version = "0.1.0"

    async def handle(self, task: Task) -> TaskResult:
        t0 = time.monotonic()
        try:
            response = await omi_run(
                message=task.message,
                session_id=task.session_id,
                context=task.context,
            )
            return TaskResult(
                task_id=task.id,
                agent_id=self.agent_id,
                status=TaskStatus.COMPLETED,
                content=response,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                agent_id=self.agent_id,
                status=TaskStatus.FAILED,
                content=f"Omi encountered an error: {e}",
                error=str(e),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

    async def health_check(self) -> bool:
        return True


async def run_agent_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    platform_url: str | None = None,
):
    """Start Omi as a platform-registered agent service."""
    await init_db()

    base_url = f"http://{host}:{port}"
    agent = HelixAgent(base_url=base_url)

    platform_url = platform_url or os.getenv("PLATFORM_URL")

    @asynccontextmanager
    async def lifespan(app):
        if platform_url:
            ok = await agent.register(platform_url)
            if ok:
                print(f"[omi] Registered with platform at {platform_url}")
                hb_task = asyncio.create_task(agent.start_heartbeat_loop(30))
            else:
                print("[omi] Platform registration failed — running standalone")
                hb_task = None
        else:
            print("[omi] No PLATFORM_URL set — running standalone")
            hb_task = None
        yield
        if hb_task:
            hb_task.cancel()
        if platform_url:
            await agent.deregister()

    app = make_agent_server(agent)
    app.router.lifespan_context = lifespan

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
