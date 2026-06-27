"""Task Executor — sends tasks to agents and persists results.

Flow:
  submit(task) → route → call agent /run → persist result → return TaskResult

Multi-agent chains:
  submit_chain([task1, task2, ...]) — output of task N becomes context for task N+1.
"""
from __future__ import annotations

import time
import uuid

import httpx

from ..dispatcher.router import route
from ..observability.tracker import record_run
from ..sdk.agent_base import Task, TaskResult, TaskStatus
from ..storage.models import save_task, update_task_result


async def submit(task: Task) -> TaskResult:
    """Route a task to the right agent and execute it."""
    task.id = task.id or str(uuid.uuid4())
    await save_task(task)

    agent = await route(task)
    if not agent:
        result = TaskResult(
            task_id=task.id, agent_id="none",
            status=TaskStatus.FAILED,
            content="No online agent available to handle this task.",
            error="no_agent",
        )
        await update_task_result(result)
        return result

    task.agent_id = agent.id
    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{agent.base_url}/run",
                json=task.model_dump(mode="json"),
            )
            resp.raise_for_status()
            result = TaskResult(**resp.json())

    except httpx.TimeoutException:
        result = TaskResult(
            task_id=task.id, agent_id=agent.id,
            status=TaskStatus.FAILED,
            content="Agent timed out.",
            error="timeout",
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as e:
        result = TaskResult(
            task_id=task.id, agent_id=agent.id,
            status=TaskStatus.FAILED,
            content=f"Agent call failed: {e}",
            error=str(e),
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    await update_task_result(result)
    await record_run(result)
    return result


async def submit_chain(tasks: list[Task]) -> list[TaskResult]:
    """Execute a sequence of tasks where each result feeds into the next."""
    results: list[TaskResult] = []
    prior_context = ""

    for i, task in enumerate(tasks):
        if prior_context:
            task.context["prior_result"] = prior_context
            task.context["chain_step"] = i

        result = await submit(task)
        results.append(result)

        if result.status == TaskStatus.FAILED:
            break                        # stop chain on failure

        prior_context = result.content   # pass output forward

    return results


async def collaborate(message: str, agent_ids: list[str], session_id: str = "") -> str:
    """Send the same task to multiple agents and synthesise their outputs.

    Useful when you want Omi (coding) + a DevOps agent to both weigh in.
    """
    sid = session_id or str(uuid.uuid4())
    tasks = [
        Task(message=message, agent_id=aid, session_id=sid)
        for aid in agent_ids
    ]
    results = [await submit(t) for t in tasks]

    parts = []
    for r in results:
        parts.append(f"**[{r.agent_id}]**\n{r.content}")
    return "\n\n---\n\n".join(parts)
