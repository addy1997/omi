"""Platform API Gateway — single entry point for all clients and agents."""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..registry.store import init_registry, start_health_monitor
from ..storage.models import init_storage
from ..observability.tracker import init_tracker
from ..dispatcher.executor import submit
from ..sdk.agent_base import Task
from .routes.agents import router as agents_router
from .routes.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_registry()
    await init_storage()
    await init_tracker()
    monitor = start_health_monitor()
    yield
    monitor.cancel()


app = FastAPI(
    title="Omi Platform",
    version="0.1.0",
    description="Multi-agent orchestration platform. Plug in any agent via the SDK.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_url, "http://localhost:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(tasks_router)


# ── Health ────────────────────────────────────────────────────

@app.get("/health", tags=["platform"])
async def health():
    from ..registry.store import list_agents
    from ..sdk.agent_base import AgentStatus
    online = await list_agents(status=AgentStatus.ONLINE)
    return {
        "status": "ok",
        "platform": "Omi Platform",
        "version": "0.1.0",
        "online_agents": len(online),
        "agents": [{"id": a.id, "name": a.name} for a in online],
    }


# ── WebSocket streaming ───────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket interface — clients send tasks, platform streams results."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"message": data}

            await websocket.send_json({"type": "start"})

            task = Task(
                message=payload.get("message", data),
                session_id=session_id,
                agent_id=payload.get("agent_id"),
                context=payload.get("context", {}),
            )

            try:
                result = await submit(task)
                await websocket.send_json({
                    "type": "result",
                    "task_id": result.task_id,
                    "agent_id": result.agent_id,
                    "content": result.content,
                    "status": result.status,
                    "tokens_used": result.tokens_used,
                    "cost_usd": result.cost_usd,
                    "duration_ms": result.duration_ms,
                })
            except Exception as e:
                await websocket.send_json({"type": "error", "content": str(e)})

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass


# ── Auth helpers ──────────────────────────────────────────────

@app.post("/auth/token", tags=["auth"])
async def get_token(sub: str = "user", role: str = "user"):
    """Issue a JWT. In production, validate credentials first."""
    from ..auth.jwt import create_token
    token = create_token(sub=sub, role=role)
    return {"access_token": token, "token_type": "bearer"}
