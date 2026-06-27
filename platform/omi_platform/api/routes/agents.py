from fastapi import APIRouter, Depends, HTTPException
from ...auth.jwt import get_current_user, optional_user
from ...registry.store import (
    register_agent, deregister_agent, get_agent,
    list_agents, heartbeat, set_status,
)
from ...sdk.agent_base import AgentInfo, AgentStatus

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/register", response_model=AgentInfo)
async def register(info: AgentInfo):
    """Agents call this on startup to join the platform."""
    return await register_agent(info)


@router.delete("/{agent_id}")
async def remove(agent_id: str, _=Depends(get_current_user)):
    ok = await deregister_agent(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    return {"status": "removed", "agent_id": agent_id}


@router.post("/{agent_id}/heartbeat")
async def ping(agent_id: str):
    """Agents call this periodically to stay marked online."""
    ok = await heartbeat(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    return {"status": "ok"}


@router.get("", response_model=list[AgentInfo])
async def get_agents(capability: str | None = None, status: AgentStatus | None = None):
    return await list_agents(capability=capability, status=status)


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_one(agent_id: str):
    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent
