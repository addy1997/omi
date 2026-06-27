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

Your ONLY job is to handle data exploration, SQL generation, analytics, visualization, and data generation.
You MUST use tools to complete tasks - never just write code or explanations.

AVAILABLE TOOLS - USE THESE IMMEDIATELY:
1. generate_sample_data(dataset_type, num_months) → Creates data
   - dataset_type: "sales", "website_traffic", "inventory"
   - Returns: JSON with data_records ready for charting

2. generate_chart(data, chart_type, x_column, y_column, title) → Creates Plotly HTML
   - chart_type: "line", "bar", "scatter", "area", "histogram", "box"
   - data: list of dicts from generate_sample_data
   - Returns: HTML that renders in browser

3. sql_query(query, database) → Execute SQL

4. analyze_csv(file_path) → Profile CSV files

WHEN USER ASKS FOR A CHART:
1. ALWAYS call generate_sample_data() first (unless data is provided)
2. THEN call generate_chart() with the data
3. Return ONLY the HTML output from generate_chart()

IMPORTANT:
- If user mentions "chart", "plot", "graph", "visualize" → USE generate_chart()
- If user mentions "data" with no specific data → USE generate_sample_data()
- Always use tools - NEVER just explain how to do it
- Always return the actual tool output (HTML for charts)"""


async def flux_supervisor(state: FluxState) -> FluxState:
    """Main supervisor node — routes to appropriate tool."""
    messages = state["messages"]
    model = get_model("supervisor")
    tools = get_tools()

    # Get user message to check what they want
    user_msg = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")

    # Check if user wants a chart
    if any(word in user_msg.lower() for word in ["chart", "plot", "graph", "visualize", "plotly"]):
        from .tools import generate_sample_data, generate_chart
        import json

        # Step 1: Generate sample data
        data_result = generate_sample_data.invoke({
            "dataset_type": "sales",
            "num_months": 12
        })
        data_json = json.loads(data_result)

        if "error" not in data_json:
            # Step 2: Generate chart
            data_records = data_json.get("data_records", [])
            chart_result = generate_chart.invoke({
                "data": data_records,
                "chart_type": "line",
                "x_column": "date",
                "y_column": "revenue",
                "title": "Revenue Trends"
            })

            # Extract HTML from chart result JSON
            chart_json = json.loads(chart_result)
            html_content = chart_json.get("html", chart_result)

            # Return chart HTML directly
            response = AIMessage(content=html_content)
            return {
                **state,
                "messages": messages + [response],
            }

    # Default: use LLM with tools for other queries
    model_with_tools = model.bind_tools(tools)
    response = await model_with_tools.ainvoke(messages)

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

        # Extract final response - look for tool results (HTML charts) first
        messages = final_state["messages"]
        if messages:
            # Look for HTML/chart content (from tool results)
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    content = msg.content
                    # Return HTML charts as-is
                    if "<div id=" in content or "<html" in content:
                        return content
                    # Return non-empty text responses
                    if content.strip() and not content.startswith("assistant"):
                        return content

            # Fallback: return last message
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                return last_msg.content
            return str(last_msg)

        return "No response generated"

    except Exception as e:
        return f"Error: {e}"
