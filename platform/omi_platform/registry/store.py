"""Agent Registry — the platform's source of truth for which agents exist and their status.

Agents register via POST /agents/register.
The platform queries the registry to route tasks.
A background heartbeat monitor marks agents offline if they stop pinging.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import Column, DateTime, String, Text, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import settings
from ..sdk.agent_base import AgentInfo, AgentStatus

_engine = create_async_engine(settings.db_url, echo=False)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class AgentRecord(Base):
    __tablename__ = "platform_agents"
    id               = Column(String, primary_key=True)
    name             = Column(String, index=True)
    description      = Column(Text)
    capabilities_csv = Column(Text)        # comma-separated
    version          = Column(String)
    base_url         = Column(String)
    status           = Column(String, default=AgentStatus.ONLINE)
    registered_at    = Column(DateTime)
    last_heartbeat   = Column(DateTime)
    metadata_json    = Column(Text, default="{}")


async def init_registry() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── CRUD ──────────────────────────────────────────────────────

async def register_agent(info: AgentInfo) -> AgentInfo:
    now = datetime.now(timezone.utc)
    async with _Session() as db:
        existing = await db.get(AgentRecord, info.id)
        if existing:
            existing.name             = info.name
            existing.description      = info.description
            existing.capabilities_csv = ",".join(info.capabilities)
            existing.version          = info.version
            existing.base_url         = info.base_url
            existing.status           = AgentStatus.ONLINE
            existing.last_heartbeat   = now
        else:
            db.add(AgentRecord(
                id=info.id, name=info.name, description=info.description,
                capabilities_csv=",".join(info.capabilities),
                version=info.version, base_url=info.base_url,
                status=AgentStatus.ONLINE,
                registered_at=now, last_heartbeat=now,
            ))
        await db.commit()
    return info


async def deregister_agent(agent_id: str) -> bool:
    async with _Session() as db:
        record = await db.get(AgentRecord, agent_id)
        if not record:
            return False
        await db.delete(record)
        await db.commit()
    return True


async def heartbeat(agent_id: str) -> bool:
    async with _Session() as db:
        result = await db.execute(
            update(AgentRecord)
            .where(AgentRecord.id == agent_id)
            .values(last_heartbeat=datetime.now(timezone.utc), status=AgentStatus.ONLINE)
        )
        await db.commit()
    return result.rowcount > 0


async def set_status(agent_id: str, status: AgentStatus) -> None:
    async with _Session() as db:
        await db.execute(
            update(AgentRecord)
            .where(AgentRecord.id == agent_id)
            .values(status=status)
        )
        await db.commit()


async def get_agent(agent_id: str) -> AgentInfo | None:
    async with _Session() as db:
        record = await db.get(AgentRecord, agent_id)
    return _to_info(record) if record else None


async def list_agents(
    capability: str | None = None,
    status: AgentStatus | None = None,
) -> list[AgentInfo]:
    async with _Session() as db:
        stmt = select(AgentRecord)
        result = await db.execute(stmt)
        records = result.scalars().all()

    agents = [_to_info(r) for r in records]
    if capability:
        agents = [a for a in agents if capability in a.capabilities]
    if status:
        agents = [a for a in agents if a.status == status]
    return agents


async def find_agents_for_task(capabilities: list[str]) -> list[AgentInfo]:
    """Return online agents that match ANY of the given capabilities."""
    online = await list_agents(status=AgentStatus.ONLINE)
    matched = []
    for agent in online:
        if any(c in agent.capabilities for c in capabilities):
            matched.append(agent)
    return matched


def _to_info(r: AgentRecord) -> AgentInfo:
    import json
    return AgentInfo(
        id=r.id, name=r.name, description=r.description,
        capabilities=r.capabilities_csv.split(",") if r.capabilities_csv else [],
        version=r.version, base_url=r.base_url,
        status=AgentStatus(r.status),
        registered_at=r.registered_at or datetime.now(timezone.utc),
        last_heartbeat=r.last_heartbeat or datetime.now(timezone.utc),
    )


# ── Health monitor ────────────────────────────────────────────

async def _health_monitor_loop() -> None:
    """Background task: mark agents offline if heartbeat is stale."""
    timeout = timedelta(seconds=settings.heartbeat_timeout_s)
    while True:
        await asyncio.sleep(settings.heartbeat_interval_s)
        cutoff = datetime.now(timezone.utc) - timeout
        async with _Session() as db:
            result = await db.execute(
                select(AgentRecord).where(
                    AgentRecord.last_heartbeat < cutoff,
                    AgentRecord.status == AgentStatus.ONLINE,
                )
            )
            stale = result.scalars().all()
            for agent in stale:
                agent.status = AgentStatus.OFFLINE
            if stale:
                await db.commit()


def start_health_monitor() -> asyncio.Task:
    return asyncio.create_task(_health_monitor_loop())
