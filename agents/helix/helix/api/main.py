"""FastAPI application — REST + WebSocket for Omi.

Endpoints:
  POST /chat              — single-turn, returns full response
  WS   /ws/{session_id}   — streaming, sends tokens as they arrive
  GET  /sessions/{id}     — fetch message history for a session
  GET  /knowledge         — list knowledge base entries
  POST /knowledge         — add a knowledge entry
  GET  /health            — liveness probe
"""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..memory.session import get_history, init_db
from ..memory.knowledge import add_learning, list_knowledge, search_knowledge
from ..supervisor.graph import run as omi_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Helix", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Helix"}


# ── Chat (REST) ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context: dict[str, Any] = {}


class ChatResponse(BaseModel):
    session_id: str
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    response = await omi_run(req.message, session_id=sid, context=req.context)
    return ChatResponse(session_id=sid, response=response)


# ── WebSocket (streaming) ─────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                message = payload.get("message", data)
                context = payload.get("context", {})
            except json.JSONDecodeError:
                message = data
                context = {}

            await websocket.send_json({"type": "start", "session_id": session_id})

            try:
                response = await omi_run(message, session_id=session_id, context=context)
                await websocket.send_json({"type": "response", "content": response})
            except Exception as e:
                await websocket.send_json({"type": "error", "content": str(e)})

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        pass


# ── Session history ───────────────────────────────────────────

@app.get("/sessions/{session_id}")
async def get_session(session_id: str, limit: int = 50):
    history = await get_history(session_id, limit=limit)
    return {"session_id": session_id, "messages": history}


# ── Knowledge base ────────────────────────────────────────────

class KnowledgeRequest(BaseModel):
    name: str
    body: str
    category: str = "convention"
    repo: str | None = None
    source_agent: str = "user"


@app.get("/knowledge")
async def get_knowledge(repo: str | None = None, limit: int = 30):
    entries = await list_knowledge(repo=repo, limit=limit)
    return {"entries": entries}


@app.get("/knowledge/search")
async def search_knowledge_route(query: str, repo: str | None = None):
    results = await search_knowledge(query, repo=repo)
    return {"results": results}


@app.post("/knowledge")
async def post_knowledge(req: KnowledgeRequest):
    result = await add_learning(
        name=req.name, body=req.body,
        category=req.category, repo=req.repo, source_agent=req.source_agent,
    )
    return {"status": "ok", "message": result}
