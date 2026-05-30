"""Task Router — decides which agent handles a given task.

Three routing modes:
  1. EXPLICIT   — task.agent_id is set → route directly, no LLM needed
  2. CAPABILITY — task.metadata["capability"] hint → match by capability
  3. LLM        — ask a small LLM to pick the best agent from the registry
"""
from __future__ import annotations

import json

import httpx
from pydantic import BaseModel

from ..config import settings
from ..registry.store import find_agents_for_task, list_agents
from ..sdk.agent_base import AgentInfo, AgentStatus, Task

# Capability keywords → Capability tags (fast pre-LLM routing)
_KEYWORD_MAP: dict[str, list[str]] = {
    "code_generation": ["write", "implement", "create", "build", "code", "function", "class", "fix bug"],
    "code_review":     ["review", "pr", "pull request", "diff", "check", "audit"],
    "code_search":     ["find", "where is", "grep", "search code", "locate", "which file"],
    "planning":        ["plan", "break down", "issues", "roadmap", "decompose", "sprint"],
    "issue_triage":    ["triage", "label", "categorise", "categorize", "issue", "backlog"],
    "web_research":    ["docs", "documentation", "error", "how to", "api", "library", "search"],
    "data_analysis":   ["analyse", "analyze", "data", "chart", "plot", "statistics", "csv"],
    "devops":          ["deploy", "ci", "cd", "pipeline", "docker", "kubernetes", "infra"],
    "testing":         ["test", "unit test", "pytest", "coverage", "mock"],
}


def _keyword_capabilities(message: str) -> list[str]:
    ml = message.lower()
    matched = []
    for cap, keywords in _KEYWORD_MAP.items():
        if any(kw in ml for kw in keywords):
            matched.append(cap)
    return matched


async def _llm_route(message: str, agents: list[AgentInfo]) -> AgentInfo | None:
    """Use a small LLM to pick the best agent when keywords don't match."""
    agent_list = "\n".join(
        f"- {a.id} ({a.name}): {a.description} | caps: {', '.join(a.capabilities)}"
        for a in agents
    )
    prompt = (
        f"You are a task router. Pick the best agent for this task.\n\n"
        f"Task: {message}\n\nAvailable agents:\n{agent_list}\n\n"
        f'Respond with JSON only: {{"agent_id": "<id>", "reason": "<one line>"}}'
    )
    try:
        import os
        api_key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={"model": "claude-haiku-4-5",
                          "max_tokens": 128,
                          "messages": [{"role": "user", "content": prompt}]},
                )
                resp.raise_for_status()
                text = resp.json()["content"][0]["text"]
                data = json.loads(text)
                agent_id = data.get("agent_id")
                return next((a for a in agents if a.id == agent_id), None)
    except Exception:
        pass
    return agents[0] if agents else None    # fallback: first online agent


async def route(task: Task) -> AgentInfo | None:
    """Resolve which agent should handle this task. Returns None if no agent available."""

    # 1. Explicit routing
    if task.agent_id:
        from ..registry.store import get_agent
        agent = await get_agent(task.agent_id)
        if agent and agent.status == AgentStatus.ONLINE:
            return agent
        return None

    # 2. Capability hint in metadata
    hint = task.metadata.get("capability")
    if hint:
        candidates = await find_agents_for_task([hint])
        if candidates:
            return candidates[0]

    # 3. Keyword matching
    caps = _keyword_capabilities(task.message)
    if caps:
        candidates = await find_agents_for_task(caps)
        if candidates:
            return candidates[0]

    # 4. LLM routing (fallback)
    all_online = await list_agents(status=AgentStatus.ONLINE)
    if not all_online:
        return None
    return await _llm_route(task.message, all_online)
