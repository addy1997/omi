"""Platform-level task persistence."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import settings
from ..sdk.agent_base import Task, TaskResult, TaskStatus

_engine = create_async_engine(settings.db_url, echo=False)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "platform_tasks"
    id           = Column(String, primary_key=True)
    session_id   = Column(String, index=True)
    agent_id     = Column(String, nullable=True, index=True)
    message      = Column(Text)
    status       = Column(String, default=TaskStatus.PENDING)
    result       = Column(Text, nullable=True)
    tokens_used  = Column(Integer, default=0)
    cost_usd     = Column(Float, default=0.0)
    duration_ms  = Column(Integer, default=0)
    error        = Column(Text, nullable=True)
    context_json = Column(Text, default="{}")
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


async def init_storage() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_task(task: Task) -> None:
    async with _Session() as db:
        db.add(TaskRecord(
            id=task.id, session_id=task.session_id,
            agent_id=task.agent_id, message=task.message,
            status=TaskStatus.PENDING,
            context_json=json.dumps(task.context),
        ))
        await db.commit()


async def update_task_result(result: TaskResult) -> None:
    async with _Session() as db:
        await db.execute(
            update(TaskRecord)
            .where(TaskRecord.id == result.task_id)
            .values(
                status=result.status,
                agent_id=result.agent_id,
                result=result.content,
                tokens_used=result.tokens_used,
                cost_usd=result.cost_usd,
                duration_ms=result.duration_ms,
                error=result.error,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()


async def get_task(task_id: str) -> TaskRecord | None:
    async with _Session() as db:
        return await db.get(TaskRecord, task_id)


async def list_tasks(
    session_id: str | None = None,
    agent_id: str | None = None,
    limit: int = 50,
) -> list[TaskRecord]:
    async with _Session() as db:
        stmt = select(TaskRecord).order_by(TaskRecord.created_at.desc()).limit(limit)
        if session_id:
            stmt = stmt.where(TaskRecord.session_id == session_id)
        if agent_id:
            stmt = stmt.where(TaskRecord.agent_id == agent_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
