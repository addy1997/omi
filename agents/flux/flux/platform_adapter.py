"""Flux platform adapter — registers as a Data agent."""
from omi_platform.sdk.agent_base import (
    AgentBase, Capability, Task, TaskResult, TaskStatus, make_agent_server,
)
from .supervisor.graph import run as flux_run
import time

class FluxAgent(AgentBase):
    name = "flux"
    description = "Flux — Data agent. SQL generation, analytics, visualization, ETL, BI integration."
    capabilities = [
        Capability.DATA_ANALYSIS,
        "sql-generation",
        "data-visualization",
        "etl-pipelines",
        "analytics",
    ]
    version = "0.1.0"

    async def handle(self, task: Task) -> TaskResult:
        t0 = time.monotonic()
        try:
            response = await flux_run(
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
    port: int = 8002,
    platform_url: str | None = None,
):
    """Start Flux as a registered platform agent."""
    import os
    import asyncio
    import uvicorn
    from contextlib import asynccontextmanager

    base_url = f"http://{host}:{port}"
    agent = FluxAgent(base_url=base_url)

    platform_url = platform_url or os.getenv("PLATFORM_URL")

    @asynccontextmanager
    async def lifespan(app):
        if platform_url:
            ok = await agent.register(platform_url)
            if ok:
                print(f"[flux] ✓ Registered with platform at {platform_url}")
                hb_task = asyncio.create_task(agent.start_heartbeat_loop(30))
            else:
                print("[flux] Registration failed — running standalone")
                hb_task = None
        else:
            print("[flux] No PLATFORM_URL set — running standalone")
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
