"""Vera supervisor — LangGraph orchestration for testing/QA tasks."""
from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from .tools import get_tools
from ..models import get_model


class VeraState(TypedDict):
    """State passed through the Vera agent graph."""
    messages: list[BaseMessage]
    session_id: str
    task_context: dict
    current_agent: str


_VERA_SYSTEM = """You are Vera, a Testing/QA specialist agent on the Omi platform.

Your job is to ensure code quality through tests: generating tests, analyzing
coverage, planning test strategy, and building mocks/fixtures.

AVAILABLE TOOLS:
- generate_unit_tests: Produce framework-specific tests for a given source file/function
- run_tests: Execute the test suite (pytest) and parse pass/fail results
- analyze_coverage: Run coverage and report which lines/branches are untested
- detect_test_gaps: Identify functions/branches with no test coverage
- generate_fixtures: Create mocks, fixtures, and test doubles for dependencies
- ask_helix: Ask the Code agent for source context or implementation details
- discover_available_agents: See which other agents are available

WORKFLOW:
1. Understand what needs testing (a function, module, bug regression, or whole suite)
2. If source is unclear, use ask_helix to get the code under test
3. Generate tests covering: happy path, edge cases, error paths, boundaries
4. Prefer table-driven/parametrized tests; isolate units with fixtures/mocks
5. Run tests and coverage; report gaps against the coverage threshold
6. Summarize: what was tested, what passed, remaining risk

CONSTRAINTS:
- Tests must be deterministic — no real network, clock, or filesystem unless mocked
- Never weaken an assertion just to make a test pass
- Name tests descriptively (test_<unit>_<condition>_<expected>)
- Flag flaky patterns (sleeps, ordering dependence) rather than embedding them
- State coverage honestly; do not claim coverage you did not measure"""


async def vera_supervisor(state: VeraState) -> VeraState:
    """Main supervisor node — orchestrates testing tasks."""
    messages = state["messages"]
    model = get_model("supervisor")
    tools = get_tools()
    model_with_tools = model.bind_tools(tools)
    response = await model_with_tools.ainvoke(messages)
    return {**state, "messages": messages + [response]}


async def should_continue(state: VeraState) -> Literal["execute_tool", "finish"]:
    """Determine if we should execute a tool or finish."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tool"
    return "finish"


async def execute_tool(state: VeraState) -> VeraState:
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


async def finish_node(state: VeraState) -> VeraState:
    """Generate final response."""
    return {**state, "messages": state["messages"]}


workflow = StateGraph(VeraState)
workflow.add_node("supervisor", vera_supervisor)
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
    """Run Vera for a testing/QA task."""
    session_id = session_id or "vera-session"
    initial_state = {
        "messages": [HumanMessage(content=f"{_VERA_SYSTEM}\n\nTask: {message}")],
        "session_id": session_id,
        "task_context": {},
        "current_agent": "vera",
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
