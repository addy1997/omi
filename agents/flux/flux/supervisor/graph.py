"""Flux supervisor — LangGraph orchestration for data analysis tasks."""
from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import StreamWriter

from .tools import get_tools
from ..models import get_model


class FluxState(TypedDict):
    """State passed through the Flux agent graph."""
    messages: list[BaseMessage]
    session_id: str
    task_context: dict
    current_agent: str


_FLUX_SYSTEM = """You are Flux, a data analysis specialist agent on the Omi platform.

Your job is to handle data exploration, SQL generation, analytics, and visualization.

AVAILABLE TOOLS:
- sql_query: Execute SQL on DuckDB or PostgreSQL
- analyze_csv: Profile and analyze CSV/Parquet files
- generate_chart: Create interactive Plotly visualizations
- web_search: Find public datasets and documentation

WORKFLOW:
1. Understand the user's data request
2. If they need SQL: write query, execute, show results
3. If they need analysis: profile data, find patterns, explain findings
4. If they need visualization: generate interactive charts with Plotly
5. Always explain your reasoning

CONSTRAINTS:
- Never modify production databases without explicit confirmation
- Always show sample results before running expensive queries
- Limit result sets to 1000 rows max
- Suggest indexes for slow queries"""


async def flux_supervisor(state: FluxState) -> FluxState:
    """Main supervisor node — routes to appropriate tool."""
    messages = state["messages"]
    model = get_model("supervisor")
    tools = get_tools()

    # Bind tools to model
    model_with_tools = model.bind_tools(tools)

    # Call model
    response = await model_with_tools.ainvoke({
        "messages": messages,
        "system": _FLUX_SYSTEM,
    })

    # Add response to messages
    return {
        **state,
        "messages": messages + [response],
    }


async def should_continue(state: FluxState) -> Literal["execute_tool", "finish"]:
    """Determine if we should execute a tool or finish."""
    messages = state["messages"]
    last_message = messages[-1]

    # If last message has tool calls, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tool"

    # Otherwise, finish
    return "finish"


async def execute_tool(state: FluxState) -> FluxState:
    """Execute tool calls from the model."""
    messages = state["messages"]
    last_message = messages[-1]

    if not hasattr(last_message, "tool_calls"):
        return state

    tools_dict = {tool.name: tool for tool in get_tools()}
    tool_results = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]

        if tool_name in tools_dict:
            tool = tools_dict[tool_name]
            result = await tool.ainvoke(tool_input) if hasattr(tool, 'ainvoke') else tool.invoke(tool_input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call["id"],
                "content": result,
            })

    # Add tool results to messages
    from langchain_core.messages import ToolMessage
    tool_messages = [
        ToolMessage(
            content=result["content"],
            tool_call_id=result["tool_use_id"],
        )
        for result in tool_results
    ]

    return {
        **state,
        "messages": messages + tool_messages,
    }


async def finish_node(state: FluxState) -> FluxState:
    """Generate final response."""
    messages = state["messages"]
    return {
        **state,
        "messages": messages,
    }


# Build the graph
workflow = StateGraph(FluxState)

workflow.add_node("supervisor", flux_supervisor)
workflow.add_node("execute_tool", execute_tool)
workflow.add_node("finish", finish_node)

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    should_continue,
    {
        "execute_tool": "execute_tool",
        "finish": "finish",
    }
)
workflow.add_edge("execute_tool", "supervisor")
workflow.add_edge("finish", END)

graph = workflow.compile()


async def run(
    message: str,
    session_id: str | None = None,
) -> str:
    """Run Flux for a data analysis task."""
    from ..config import settings

    session_id = session_id or "flux-session"

    initial_state = {
        "messages": [HumanMessage(content=message)],
        "session_id": session_id,
        "task_context": {},
        "current_agent": "flux",
    }

    # Run the graph
    try:
        final_state = await graph.ainvoke(initial_state)

        # Extract final response
        messages = final_state["messages"]
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                return last_msg.content
            return str(last_msg)

        return "No response generated"

    except Exception as e:
        return f"Error: {e}"
