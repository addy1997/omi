"""Omi supervisor — LangGraph state machine that routes tasks to specialist agents."""
from __future__ import annotations

import time
import uuid
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from ..agents import coder, explorer, planner, researcher, triager
from ..models import get_model

# ── State ─────────────────────────────────────────────────────

Agent = Literal["coder", "explorer", "planner", "researcher", "triager", "finish"]


class HelixState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: Agent
    session_id: str
    task_context: dict
    total_tokens: int
    total_cost_usd: float


# ── System prompts ────────────────────────────────────────────

_ROUTER_SYSTEM = """You are Helix, a coding agent supervisor on the Omi multi-agent platform.
Read the conversation and decide which specialist to call next.

LOCAL AGENTS (within Helix)
- coder      → write/edit/test/commit/PR code; bug fixes; refactoring
- explorer   → read-only code search; PR review; architecture questions
- planner    → break features into GitHub issues; roadmap; decomposition
- researcher → web search for docs, APIs, errors, best practices
- triager    → categorise/label/manage GitHub issues

PLATFORM AGENTS (delegate via ask_* tools)
- ask_flux   → data analysis, SQL queries, Plotly chart generation, data visualization
- ask_nexus  → infrastructure, DevOps, deployment, monitoring

DECISION RULES:
1. If task is about data analysis, visualization, charts, SQL → delegate to Flux
2. If task is about infrastructure, deployment, cloud → delegate to Nexus
3. If task is about code → route to coder
4. If task is about exploration/review → route to explorer
5. Default to finish for conversational, factual, or already-answered

Reply with ONLY this JSON (no markdown):
{{"next": "<agent_or_finish>", "reason": "<one line>"}}"""

_DIRECT_SYSTEM = """You are Helix, a helpful AI coding assistant.
Answer the user's question directly, clearly, and concisely.
You specialise in software engineering, robotics, AI, and coding topics."""

_router_msg  = SystemMessage(content=_ROUTER_SYSTEM)
_direct_msg  = SystemMessage(content=_DIRECT_SYSTEM)
_parser      = JsonOutputParser()


# ── Nodes ─────────────────────────────────────────────────────

def supervisor_node(state: HelixState) -> dict:
    """Route to the right specialist, or to finish for direct answers."""
    messages = [_router_msg] + list(state["messages"])
    raw = get_model("supervisor").invoke(messages)
    try:
        result = _parser.invoke(raw)
    except Exception:
        result = {}

    next_agent: Agent = result.get("next", "finish").lower()
    if next_agent not in ("coder", "explorer", "planner", "researcher", "triager", "finish"):
        next_agent = "finish"
    return {"next_agent": next_agent}


def finish_node(state: HelixState) -> dict:
    """Generate a direct response without delegating to a specialist."""
    messages = [_direct_msg] + list(state["messages"])
    response = get_model("supervisor").invoke(messages)
    return {"messages": [AIMessage(content=response.content)]}


def _make_agent_node(role: str, agent_graph):
    def node(state: HelixState) -> dict:
        last_human = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            "",
        )
        result = agent_graph.invoke({"messages": [HumanMessage(content=last_human)]})
        agent_messages = result.get("messages", [])
        final = agent_messages[-1].content if agent_messages else f"{role} returned no output."
        return {
            "messages": [AIMessage(content=f"[{role.upper()}] {final}")],
            "next_agent": "finish",
        }
    node.__name__ = role
    return node


def _route(state: HelixState) -> str:
    return state["next_agent"]   # "finish" | "coder" | "explorer" | ...


# ── Build the graph ───────────────────────────────────────────

def build_graph():
    agents = {
        "coder":      coder.build(),
        "explorer":   explorer.build(),
        "planner":    planner.build(),
        "researcher": researcher.build(),
        "triager":    triager.build(),
    }

    builder = StateGraph(HelixState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("finish",     finish_node)
    for role, agent in agents.items():
        builder.add_node(role, _make_agent_node(role, agent))

    builder.add_conditional_edges(
        "supervisor",
        _route,
        {
            "finish":     "finish",
            "coder":      "coder",
            "explorer":   "explorer",
            "planner":    "planner",
            "researcher": "researcher",
            "triager":    "triager",
        },
    )

    # finish ends the graph
    builder.add_edge("finish", END)

    # after each specialist, go back to supervisor for re-routing
    for role in agents:
        builder.add_edge(role, "supervisor")

    builder.add_edge(START, "supervisor")
    return builder.compile()


# ── Public run function ───────────────────────────────────────

async def run(
    message: str,
    session_id: str | None = None,
    context: dict | None = None,
) -> str:
    from ..memory.session import get_history, save_message, log_run

    sid = session_id or str(uuid.uuid4())
    history = await get_history(sid)

    prior_messages: list[BaseMessage] = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in history
    ]

    await save_message(sid, "user", message)
    t0 = time.monotonic()

    graph = build_graph()
    initial_state: HelixState = {
        "messages": prior_messages + [HumanMessage(content=message)],
        "next_agent": "supervisor",
        "session_id": sid,
        "task_context": context or {},
        "total_tokens": 0,
        "total_cost_usd": 0.0,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        ai_messages = [m for m in final_state["messages"] if isinstance(m, AIMessage)]
        response = ai_messages[-1].content if ai_messages else "No response generated."
    except Exception as e:
        response = f"Error: {e}"

    duration_ms = int((time.monotonic() - t0) * 1000)
    await save_message(sid, "assistant", response)
    await log_run(sid, "supervisor", message, response, duration_ms=duration_ms)

    return response
