"""Nexus supervisor — LangGraph orchestration for DevOps tasks."""
from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

from .tools import get_tools
from ..models import get_model


class NexusState(TypedDict):
    """State passed through the Nexus agent graph."""
    messages: list[BaseMessage]
    session_id: str
    task_context: dict
    current_agent: str


_NEXUS_SYSTEM = """You are Nexus, a DevOps specialist agent on the Omi platform.

Your job is to handle infrastructure, deployments, monitoring, and incident response.

AVAILABLE TOOLS:
- docker_cmd: Run Docker commands (build, push, run containers)
- k8s_deploy: Deploy to Kubernetes (create manifests, apply, check status)
- monitor_health: Check system health (CPU, memory, disk, service status)
- cloud_info: Get information about cloud infrastructure (AWS, GCP, Azure)
- terraform_plan: Analyze Terraform infrastructure-as-code changes

WORKFLOW:
1. Understand the DevOps task (deploy, scale, monitor, troubleshoot)
2. If deploying: write manifests/configs, validate, apply changes
3. If monitoring: check system health, alert on issues
4. If incident response: diagnose issues, suggest fixes
5. Always show what you're about to do before executing

CONSTRAINTS:
- Never apply changes without explicit confirmation in production
- Always show a plan/preview before executing
- Validate infrastructure changes with dry-run first
- Never delete resources without triple-checking
- Always maintain high availability"""


async def nexus_supervisor(state: NexusState) -> NexusState:
    """Main supervisor node — orchestrates DevOps tasks."""
    messages = state["messages"]
    model = get_model("supervisor")
    tools = get_tools()

    # Bind tools to model
    model_with_tools = model.bind_tools(tools)

    # Call model with messages
    response = await model_with_tools.ainvoke(messages)

    # Add response to messages
    return {
        **state,
        "messages": messages + [response],
    }


async def should_continue(state: NexusState) -> Literal["execute_tool", "finish"]:
    """Determine if we should execute a tool or finish."""
    messages = state["messages"]
    last_message = messages[-1]

    # If last message has tool calls, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tool"

    # Otherwise, finish
    return "finish"


async def execute_tool(state: NexusState) -> NexusState:
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


async def finish_node(state: NexusState) -> NexusState:
    """Generate final response."""
    messages = state["messages"]
    return {
        **state,
        "messages": messages,
    }


# Build the graph
workflow = StateGraph(NexusState)

workflow.add_node("supervisor", nexus_supervisor)
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
    """Run Nexus for a DevOps task."""
    from ..config import settings

    session_id = session_id or "nexus-session"

    initial_state = {
        "messages": [HumanMessage(content=message)],
        "session_id": session_id,
        "task_context": {},
        "current_agent": "nexus",
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
