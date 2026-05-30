"""Shared vector knowledge base — agents learn project conventions here.

Uses pgvector in production, falls back to naive cosine search with numpy in dev.
All agents can read/write to the same knowledge base (like Coda's LearningMachine).
"""
from __future__ import annotations

import json
import time
from typing import Literal

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings
from .session import Base, _engine, _SessionLocal

KnowledgeCategory = Literal["convention", "architecture", "gotcha", "preference", "process", "bug"]


class KnowledgeEntry(Base):
    __tablename__ = "omi_knowledge"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    body = Column(Text)
    repo = Column(String, nullable=True, index=True)
    source_agent = Column(String, nullable=True)
    embedding_json = Column(Text, nullable=True)   # JSON list[float]
    created_at = Column(Float, default=time.time)


def _embed(text: str) -> list[float] | None:
    """Embed text. Uses OpenAI if available, returns None otherwise."""
    try:
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        resp = client.embeddings.create(model="text-embedding-3-small", input=text[:8000])
        return resp.data[0].embedding
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-9)


async def add_learning(
    name: str,
    body: str,
    category: KnowledgeCategory = "convention",
    repo: str | None = None,
    source_agent: str | None = None,
) -> str:
    embedding = _embed(f"{name}: {body}")
    async with _SessionLocal() as db:
        db.add(KnowledgeEntry(
            name=name, category=category, body=body,
            repo=repo, source_agent=source_agent,
            embedding_json=json.dumps(embedding) if embedding else None,
        ))
        await db.commit()
    return f"Learned: [{category}] {name}"


async def search_knowledge(
    query: str,
    repo: str | None = None,
    limit: int = 8,
) -> str:
    async with _SessionLocal() as db:
        stmt = select(KnowledgeEntry).order_by(KnowledgeEntry.created_at.desc()).limit(200)
        if repo:
            stmt = stmt.where(
                (KnowledgeEntry.repo == repo) | (KnowledgeEntry.repo.is_(None))
            )
        result = await db.execute(stmt)
        entries = result.scalars().all()

    if not entries:
        return "No knowledge entries found."

    query_emb = _embed(query)
    if query_emb:
        ranked = sorted(
            entries,
            key=lambda e: _cosine(query_emb, json.loads(e.embedding_json))
            if e.embedding_json else 0.0,
            reverse=True,
        )[:limit]
    else:
        # Fall back to keyword match
        ql = query.lower()
        ranked = [e for e in entries if ql in e.name.lower() or ql in e.body.lower()][:limit]

    if not ranked:
        return "No relevant knowledge found."

    lines = [f"[{e.category}] **{e.name}** (repo:{e.repo or 'global'})\n{e.body}"
             for e in ranked]
    return "\n\n---\n\n".join(lines)


async def list_knowledge(repo: str | None = None, limit: int = 30) -> str:
    async with _SessionLocal() as db:
        stmt = select(KnowledgeEntry).order_by(KnowledgeEntry.created_at.desc()).limit(limit)
        if repo:
            stmt = stmt.where(KnowledgeEntry.repo == repo)
        result = await db.execute(stmt)
        entries = result.scalars().all()
    if not entries:
        return "Knowledge base is empty."
    return "\n".join(f"• [{e.category}] {e.name}" for e in entries)
