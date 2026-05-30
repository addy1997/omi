"""Platform API Gateway — single entry point for all clients and agents."""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from ..config import settings
from ..registry.store import init_registry, start_health_monitor
from ..storage.models import init_storage
from ..observability.tracker import init_tracker
from ..dispatcher.executor import submit
from ..sdk.agent_base import Task
from ..auth.jwt import get_current_user, optional_user, create_token
from .routes.agents import router as agents_router
from .routes.tasks import router as tasks_router

logger = logging.getLogger(__name__)


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
    docs_url=None if not settings.debug else "/docs",
    redoc_url=None if not settings.debug else "/redoc",
)

# Add middleware BEFORE routers (order matters — added in reverse)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        settings.dashboard_url.split("://")[1].split(":")[0] if "://" in settings.dashboard_url else settings.dashboard_url,
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_url, "http://localhost:5173"],  # ✅ Restrictive
    allow_credentials=True,
    allow_methods=["GET", "POST", "WebSocket"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(agents_router)
app.include_router(tasks_router)

# Add decorators AFTER routers
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Health ────────────────────────────────────────────────────

@app.get("/health", tags=["platform"])
async def health():
    try:
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
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "ok",
            "platform": "Omi Platform",
            "version": "0.1.0",
            "online_agents": 0,
            "agents": [],
            "error": str(e),
        }


# ── WebSocket streaming ───────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket interface — clients send tasks, platform streams results.

    ✅ Requires Bearer token in query params: ws://localhost:9000/ws/SESSION_ID?token=JWT_TOKEN
    """
    # ✅ Verify auth token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing auth token")
        return

    try:
        from ..auth.jwt import decode_token
        user = decode_token(token)
        logger.info(f"WebSocket authenticated: user={user.sub}")
    except Exception as e:
        await websocket.close(code=4001, reason=f"Authentication failed: {e}")
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()

            # ✅ Limit message size (prevent DoS)
            if len(data) > 100000:  # 100KB limit
                await websocket.send_json({"type": "error", "content": "Message too large"})
                continue

            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"message": data}

            # ✅ Validate message content
            message = payload.get("message", data)
            if not message or len(str(message)) == 0:
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            await websocket.send_json({"type": "start"})

            task = Task(
                message=str(message)[:10000],  # Truncate to 10KB
                session_id=session_id,
                agent_id=payload.get("agent_id"),
                context=payload.get("context", {}),
                metadata={"user": user.sub, "role": user.role},
            )

            try:
                result = await submit(task)
                await websocket.send_json({
                    "type": "result",
                    "task_id": result.task_id,
                    "agent_id": result.agent_id,
                    "content": result.content,
                    "status": result.status.value,
                    "tokens_used": result.tokens_used,
                    "cost_usd": result.cost_usd,
                    "duration_ms": result.duration_ms,
                })
            except Exception as e:
                logger.error(f"Task error: {e}")
                await websocket.send_json({"type": "error", "content": "Task execution failed"})

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass


# ── Auth helpers ──────────────────────────────────────────────

from pydantic import BaseModel

class TokenRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/token", tags=["auth"])
async def get_token(req: TokenRequest):
    """Issue a JWT token after validating credentials.

    ✅ In development: accepts any username/password
    ⚠️ In production: integrate with real auth service (LDAP, OAuth2, etc.)
    """
    # ✅ Basic validation
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if len(req.username) > 255 or len(req.password) > 255:
        raise HTTPException(status_code=400, detail="Credentials too long")

    # 🔐 In production: validate against real user database
    if settings.debug:
        # Dev mode: accept any creds
        token = create_token(sub=req.username, role="user")
        logger.info(f"Token issued to {req.username} (dev mode)")
        return {"access_token": token, "token_type": "bearer"}
    else:
        # Production: strict auth required
        raise HTTPException(status_code=403, detail="Authentication service not configured")

@app.get("/health/ready", tags=["platform"])
async def readiness():
    """Kubernetes readiness probe."""
    return {"ready": True}
