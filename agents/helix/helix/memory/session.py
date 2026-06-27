"""Session and message history persistence using SQLAlchemy (SQLite dev / Postgres prod)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import settings

_engine = create_async_engine(settings.db_url, echo=False)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "omi_sessions"
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    metadata_json = Column(Text, default="{}")


class Message(Base):
    __tablename__ = "omi_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)
    role = Column(String)          # user | assistant | tool
    content = Column(Text)
    tool_name = Column(String, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(String, default="0.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RunLog(Base):
    __tablename__ = "omi_run_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)
    agent = Column(String)
    task = Column(Text)
    result = Column(Text)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(String, default="0.0")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


async def init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_message(
    session_id: str,
    role: str,
    content: str,
    tool_name: str | None = None,
    tokens: int = 0,
    cost: float = 0.0,
) -> None:
    async with _SessionLocal() as db:
        db.add(Message(
            session_id=session_id, role=role, content=content,
            tool_name=tool_name, tokens_used=tokens, cost_usd=str(cost),
        ))
        await db.commit()


async def get_history(session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    async with _SessionLocal() as db:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
    return [
        {"role": m.role, "content": m.content, "tool": m.tool_name}
        for m in reversed(rows)
    ]


async def log_run(
    session_id: str,
    agent: str,
    task: str,
    result: str,
    tokens: int = 0,
    cost: float = 0.0,
    duration_ms: int = 0,
) -> None:
    async with _SessionLocal() as db:
        db.add(RunLog(
            session_id=session_id, agent=agent, task=task, result=result,
            total_tokens=tokens, total_cost_usd=str(cost), duration_ms=duration_ms,
        ))
        await db.commit()
