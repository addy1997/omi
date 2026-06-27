from fastapi import APIRouter, HTTPException
from ...dispatcher.executor import submit, submit_chain, collaborate
from ...sdk.agent_base import Task, TaskResult
from ...storage.models import get_task, list_tasks
from ...observability.tracker import get_usage_summary, get_per_agent_usage

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResult)
async def run_task(task: Task):
    """Submit a task. Platform auto-routes to the best available agent."""
    return await submit(task)


@router.post("/chain", response_model=list[TaskResult])
async def run_chain(tasks: list[Task]):
    """Run a sequence of tasks — output of each feeds into the next."""
    if not tasks:
        raise HTTPException(400, "No tasks provided")
    return await submit_chain(tasks)


@router.post("/collaborate", response_model=dict)
async def run_collaborate(message: str, agent_ids: list[str], session_id: str = ""):
    """Send the same task to multiple agents and get a combined response."""
    result = await collaborate(message, agent_ids, session_id)
    return {"result": result}


@router.get("/{task_id}")
async def get_one(task_id: str):
    task = await get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.get("")
async def get_tasks(session_id: str | None = None, agent_id: str | None = None, limit: int = 50):
    return await list_tasks(session_id=session_id, agent_id=agent_id, limit=limit)


@router.get("/usage/summary")
async def usage_summary(agent_id: str | None = None):
    return await get_usage_summary(agent_id=agent_id)


@router.get("/usage/per-agent")
async def per_agent():
    return await get_per_agent_usage()
