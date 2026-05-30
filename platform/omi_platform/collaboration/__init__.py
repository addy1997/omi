"""Agent collaboration module — inter-agent discovery and task delegation."""
from .tools import get_collaboration_tools, discover_agents, delegate_task, get_agent_capabilities

__all__ = [
    "get_collaboration_tools",
    "discover_agents",
    "delegate_task",
    "get_agent_capabilities",
]
