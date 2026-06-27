"""Lumen supervisor — LangGraph orchestration for documentation tasks."""
from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from .tools import get_tools
from ..models import get_model


class LumenState(TypedDict):
    """State passed through the Lumen agent graph."""
    messages: list[BaseMessage]
    session_id: str
    task_context: dict
    current_agent: str


_LUMEN_SYSTEM = """You are Lumen, a Documentation specialist agent on the Omi platform.

Your job is to make code understandable: docstrings, READMEs, API reference,
architecture notes, and changelogs — accurate, concise, and matching the
codebase's existing style.

AVAILABLE TOOLS:
- extract_api_surface: Parse a source file's public functions/classes/signatures
- check_doc_coverage: Report which public symbols lack docstrings
- generate_changelog: Summarize changes from recent git history
- read_project_context: Read key files (pyproject, existing README) for grounding
- ask_helix: Ask the Code agent for implementation details you must document accurately
- discover_available_agents: See which other agents are available

WORKFLOW:
1. Identify the doc artifact requested (docstrings, README, API ref, changelog, arch doc)
2. Ground yourself: extract the real API surface and read existing context first
3. Write docs that match the detected docstring style and project conventions
4. For docstrings: describe purpose, args, returns, raises — not line-by-line behavior
5. For READMEs: what it is, install, quickstart, key concepts, links
6. Never invent parameters, return types, or behavior — verify via tools or ask_helix

CONSTRAINTS:
- Accuracy over completeness: do not document behavior you have not confirmed
- Match existing style (docstring convention, heading depth, tone)
- Keep comments/docs about intent and contracts, not restating the code
- Flag stale or contradictory existing docs rather than silently overwriting"""


async def lumen_supervisor(state: LumenState) -> LumenState:
    """Main supervisor node — orchestrates documentation tasks."""
    messages = state["messages"]
    model = get_model("supervisor")
    tools = get_tools()
    model_with_tools = model.bind_tools(tools)
    response = await model_with_tools.ainvoke(messages)
    return {**state, "messages": messages + [response]}


async def should_continue(state: LumenState) -> Literal["execute_tool", "finish"]:
    """Determine if we should execute a tool or finish."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tool"
    return "finish"


async def execute_tool(state: LumenState) -> LumenState:
    """Execute tool calls from the model."""
    messages = state["messages"]
    last_message = messages[-1]
    if not hasattr(last_message, "tool_calls"):
        return state

    tools_dict = {tool.name: tool for tool in get_tools()}
    from langchain_core.messages import ToolMessage
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        if tool_name not in tools_dict:
            tool_messages.append(ToolMessage(
                content=f"Error: unknown tool '{tool_name}'", tool_call_id=tool_call["id"]))
            continue
        tool = tools_dict[tool_name]
        try:
            result = await tool.ainvoke(tool_input) if hasattr(tool, "ainvoke") else tool.invoke(tool_input)
        except Exception as e:
            # Feed the error back so the model can fix its arguments and retry,
            # rather than aborting the whole graph (small local models often
            # emit malformed tool args).
            result = f"Tool '{tool_name}' failed: {e}. Re-check the argument types and call it again."
        tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    return {**state, "messages": messages + tool_messages}


async def finish_node(state: LumenState) -> LumenState:
    """Generate final response."""
    return {**state, "messages": state["messages"]}


workflow = StateGraph(LumenState)
workflow.add_node("supervisor", lumen_supervisor)
workflow.add_node("execute_tool", execute_tool)
workflow.add_node("finish", finish_node)
workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    should_continue,
    {"execute_tool": "execute_tool", "finish": "finish"},
)
workflow.add_edge("execute_tool", "supervisor")
workflow.add_edge("finish", END)
graph = workflow.compile()


async def run(message: str, session_id: str | None = None) -> str:
    """Run Lumen for a documentation task."""
    session_id = session_id or "lumen-session"
    initial_state = {
        "messages": [HumanMessage(content=f"{_LUMEN_SYSTEM}\n\nTask: {message}")],
        "session_id": session_id,
        "task_context": {},
        "current_agent": "lumen",
    }
    try:
        final_state = await graph.ainvoke(initial_state)
        messages = final_state["messages"]
        if messages:
            last_msg = messages[-1]
            return last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        return "No response generated"
    except Exception as e:
        return f"Error: {e}"
