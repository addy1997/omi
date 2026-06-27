"""Usage and cost tracking across all agents on the platform."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import settings
from ..sdk.agent_base import TaskResult

_engine = create_async_engine(settings.db_url, echo=False)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UsageRecord(Base):
    __tablename__ = "platform_usage"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    task_id      = Column(String, index=True)
    agent_id     = Column(String, index=True)
    tokens_used  = Column(Integer, default=0)
    cost_usd     = Column(Float, default=0.0)
    duration_ms  = Column(Integer, default=0)
    status       = Column(String)
    recorded_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))


async def init_tracker() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def record_run(result: TaskResult) -> None:
    async with _Session() as db:
        db.add(UsageRecord(
            task_id=result.task_id, agent_id=result.agent_id,
            tokens_used=result.tokens_used, cost_usd=result.cost_usd,
            duration_ms=result.duration_ms, status=result.status,
        ))
        await db.commit()


async def get_usage_summary(agent_id: str | None = None) -> dict:
    async with _Session() as db:
        stmt = select(
            func.count(UsageRecord.id).label("total_tasks"),
            func.sum(UsageRecord.tokens_used).label("total_tokens"),
            func.sum(UsageRecord.cost_usd).label("total_cost_usd"),
            func.avg(UsageRecord.duration_ms).label("avg_duration_ms"),
        )
        if agent_id:
            stmt = stmt.where(UsageRecord.agent_id == agent_id)
        result = await db.execute(stmt)
        row = result.one()

    return {
        "total_tasks":     row.total_tasks or 0,
        "total_tokens":    row.total_tokens or 0,
        "total_cost_usd":  round(row.total_cost_usd or 0.0, 6),
        "avg_duration_ms": int(row.avg_duration_ms or 0),
        "agent_id":        agent_id or "all",
    }


async def get_per_agent_usage() -> list[dict]:
    async with _Session() as db:
        stmt = select(
            UsageRecord.agent_id,
            func.count(UsageRecord.id).label("tasks"),
            func.sum(UsageRecord.tokens_used).label("tokens"),
            func.sum(UsageRecord.cost_usd).label("cost"),
        ).group_by(UsageRecord.agent_id)
        result = await db.execute(stmt)
        rows = result.all()

    return [
        {"agent_id": r.agent_id, "tasks": r.tasks,
         "tokens": r.tokens or 0, "cost_usd": round(r.cost or 0.0, 6)}
        for r in rows
    ]
