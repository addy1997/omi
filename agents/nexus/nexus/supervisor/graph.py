"""Nexus supervisor — LangGraph orchestration for DevOps tasks."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

_NEXUS_SYSTEM = """You are Nexus, a DevOps specialist agent.

Your job is to handle infrastructure, deployments, monitoring, and incident response.

CAPABILITIES
- Infrastructure as Code (Terraform, CloudFormation)
- Kubernetes deployment and management
- Docker image building and pushing
- Cloud provider operations (AWS, GCP, Azure)
- Monitoring setup (Prometheus, Grafana)
- Log aggregation and analysis
- Incident response and auto-remediation
- Performance optimization

ROUTING RULES
1. If the user wants cloud deployment → handle directly
2. If the user needs Kubernetes operations → handle directly
3. If the user wants monitoring setup → handle directly
4. If the user wants infrastructure as code → handle directly
5. Otherwise → summarize what you'd do

Always be cautious with production environments."""

_system_msg = SystemMessage(content=_NEXUS_SYSTEM)
_parser = JsonOutputParser()

async def run(
    message: str,
    session_id: str | None = None,
) -> str:
    """Run Nexus supervisor for a DevOps task."""
    from ..config import settings
    from omi_platform.sdk.agent_base import AgentBase

    return f"""[Nexus] DevOps Task: {message}

Capabilities available:
• Cloud deployment (AWS/GCP/Azure)
• Kubernetes management
• Docker operations
• Infrastructure as Code
• Monitoring & alerts
• Incident response

Status: Ready to handle DevOps operations.
Connect to platform at http://localhost:9000 to submit tasks."""
