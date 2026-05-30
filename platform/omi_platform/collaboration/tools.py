"""Inter-agent collaboration tools — agents discovering and calling each other."""
from typing import Annotated
from langchain_core.tools import tool
import json
import httpx

# Platform base URL (agents will discover this from env)
PLATFORM_URL = "http://localhost:9000"


@tool
async def discover_agents(
    capability: Annotated[str, "Filter by capability (e.g., 'code_generation', 'data_analysis')"] = None,
) -> str:
    """Discover available agents on the platform and their capabilities.

    Returns list of agents with names, capabilities, and descriptions.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PLATFORM_URL}/agents")
            response.raise_for_status()
            agents = response.json()

            # Filter by capability if provided
            if capability:
                agents = [
                    a for a in agents
                    if capability.lower() in [c.lower() for c in a.get("capabilities", [])]
                ]

            # Format for LLM consumption
            result = []
            for agent in agents:
                result.append({
                    "name": agent["name"],
                    "id": agent["id"],
                    "status": agent["status"],
                    "capabilities": agent.get("capabilities", [])[:5],  # Limit to 5
                    "description": agent.get("description", ""),
                })

            return json.dumps({
                "agents": result,
                "count": len(result),
                "filter_applied": capability if capability else "none",
            })

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def delegate_task(
    target_agent: Annotated[str, "Agent name or ID to delegate to (e.g., 'helix', 'flux', 'nexus')"],
    task_message: Annotated[str, "Task description for the other agent"],
    timeout_seconds: Annotated[int, "Max wait time for response (default 120)"] = 120,
) -> str:
    """Delegate a subtask to another agent on the platform.

    Submits a task to another agent and waits for completion.
    Use this when you need help from a specialist agent.

    Examples:
    - Flux: "Please review this SQL for performance issues"
    - Helix: "Generate code for this API endpoint"
    - Nexus: "Check if our Kubernetes cluster is healthy"
    """
    try:
        # Map agent names to IDs (basic lookup)
        name_to_id = {
            "helix": "helix",
            "flux": "flux",
            "nexus": "nexus",
        }

        agent_id = name_to_id.get(target_agent.lower(), target_agent)

        # Submit task to platform
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            task_data = {
                "message": task_message,
                "agent_id": agent_id,  # Route to specific agent
            }

            response = await client.post(
                f"{PLATFORM_URL}/tasks",
                json=task_data,
            )
            response.raise_for_status()
            result = response.json()

            # Return structured result
            return json.dumps({
                "success": result.get("status") == "completed",
                "agent": result.get("agent_id", "unknown"),
                "status": result.get("status"),
                "result": result.get("content", ""),
                "duration_ms": result.get("duration_ms", 0),
                "error": result.get("error"),
            })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
        })


@tool
async def get_agent_capabilities(
    agent_name: Annotated[str, "Agent name (helix, flux, or nexus)"],
) -> str:
    """Get detailed capabilities of a specific agent.

    Use this to understand what another agent can do before delegating.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PLATFORM_URL}/agents")
            response.raise_for_status()
            agents = response.json()

            # Find agent by name
            target = None
            for agent in agents:
                if agent["name"].lower() == agent_name.lower():
                    target = agent
                    break

            if not target:
                return json.dumps({"error": f"Agent '{agent_name}' not found"})

            return json.dumps({
                "name": target["name"],
                "description": target.get("description", ""),
                "status": target["status"],
                "capabilities": target.get("capabilities", []),
                "version": target.get("version", "unknown"),
            })

    except Exception as e:
        return json.dumps({"error": str(e)})


def get_collaboration_tools():
    """Return list of collaboration tools."""
    return [
        discover_agents,
        delegate_task,
        get_agent_capabilities,
    ]
