"""Shared agent construction helpers."""
from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from ..models import get_model


def make_agent(role: str, tools: list, system_prompt: str):
    """Return a compiled LangGraph ReAct agent for the given role."""
    model = get_model(role).bind_tools(tools)
    return create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,   # LangGraph >=0.3 uses 'prompt', not 'state_modifier'
    )
