"""Lumen platform adapter — registers as a Documentation agent."""
import time

from omi_platform.sdk.agent_base import (
    AgentBase, Capability, Task, TaskResult, TaskStatus, make_agent_server,
)
from .supervisor.graph import run as lumen_run


class LumenAgent(AgentBase):
    name = "lumen"
    description = "Lumen — Documentation agent. Docstrings, READMEs, API reference, architecture docs, changelogs, doc-coverage analysis."
    capabilities = [
        Capability.DOCUMENTATION,
        "docstring-generation",
        "readme-generation",
        "api-reference",
        "changelog-generation",
    ]
    version = "0.1.0"

    async def handle(self, task: Task) -> TaskResult:
        t0 = time.monotonic()
        try:
            response = await lumen_run(
                message=task.message,
                session_id=task.session_id,
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
                content=f"Error: {e}",
                error=str(e),
                duration_ms=int((time.monotonic() - t0) * 1000),
            )

    async def health_check(self) -> bool:
        return True


async def run_agent_server(
    host: str = "0.0.0.0",
    port: int = 8005,
    platform_url: str | None = None,
):
    """Start Lumen as a registered platform agent."""
    import os
    import asyncio
    import uvicorn
    from contextlib import asynccontextmanager

    base_url = f"http://{host}:{port}"
    agent = LumenAgent(base_url=base_url)

    platform_url = platform_url or os.getenv("PLATFORM_URL")

    @asynccontextmanager
    async def lifespan(app):
        if platform_url:
            ok = await agent.register(platform_url)
            if ok:
                print(f"[lumen] ✓ Registered with platform at {platform_url}")
                hb_task = asyncio.create_task(agent.start_heartbeat_loop(30))
            else:
                print("[lumen] Registration failed — running standalone")
                hb_task = None
        else:
            print("[lumen] No PLATFORM_URL set — running standalone")
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
