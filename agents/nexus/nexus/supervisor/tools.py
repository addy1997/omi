"""DevOps tools for Nexus agent."""
from typing import Annotated
from langchain_core.tools import tool
import json
import subprocess


@tool
def docker_cmd(
    command: Annotated[str, "Docker command to run (e.g., 'build -t myapp:latest .' or 'ps')"],
    dry_run: Annotated[bool, "Show what would happen without executing"] = False,
) -> str:
    """Execute Docker command safely.

    Supports: build, push, run, ps, stop, logs, inspect
    """
    try:
        # Whitelist safe commands
        safe_cmds = ["build", "push", "run", "ps", "stop", "logs", "inspect", "pull", "images"]
        if not any(cmd in command for cmd in safe_cmds):
            return json.dumps({"error": f"Command not allowed. Safe: {safe_cmds}"})

        if dry_run:
            return json.dumps({
                "dry_run": True,
                "command": f"docker {command}",
                "message": "Would execute above command",
            })

        # Execute Docker command
        result = subprocess.run(
            f"docker {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

        return json.dumps({
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
            "returncode": result.returncode,
        })

    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def k8s_deploy(
    action: Annotated[str, "apply (deploy), get (status), delete, describe, logs"],
    resource: Annotated[str, "K8s resource: deployment, service, pod, etc."],
    namespace: Annotated[str, "Kubernetes namespace (default: default)"] = "default",
) -> str:
    """Manage Kubernetes deployments and resources.

    Actions: apply, get, delete, describe, logs
    """
    try:
        safe_actions = ["apply", "get", "delete", "describe", "logs"]
        if action not in safe_actions:
            return json.dumps({"error": f"Action not allowed. Safe: {safe_actions}"})

        if action == "apply":
            return json.dumps({
                "message": "Use kubectl apply -f manifest.yaml",
                "example": "kubectl apply -f deployment.yaml -n default",
            })

        # Execute kubectl command
        cmd = f"kubectl {action} {resource} -n {namespace}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        return json.dumps({
            "action": action,
            "resource": resource,
            "namespace": namespace,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
            "returncode": result.returncode,
        })

    except subprocess.TimeoutExpired:
        return json.dumps({"error": "kubectl command timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def monitor_health(
    target: Annotated[str, "What to monitor: system, docker, k8s, service"],
) -> str:
    """Check health of infrastructure components.

    Targets: system (CPU/memory), docker (containers), k8s (cluster)
    """
    try:
        if target == "system":
            # Get system stats
            import psutil
            return json.dumps({
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": psutil.virtual_memory()._asdict(),
                "disk": psutil.disk_usage("/")._asdict(),
            })

        elif target == "docker":
            result = subprocess.run(
                "docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return json.dumps({
                "containers": result.stdout,
            })

        elif target == "k8s":
            result = subprocess.run(
                "kubectl get nodes -o wide",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return json.dumps({
                "nodes": result.stdout,
            })

        else:
            return json.dumps({"error": f"Unknown target: {target}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def cloud_info(
    provider: Annotated[str, "aws, gcp, or azure"],
    resource_type: Annotated[str, "ec2, rds, storage, functions, etc."],
) -> str:
    """Get information about cloud infrastructure.

    Requires configured credentials (AWS_PROFILE, GOOGLE_APPLICATION_CREDENTIALS, etc.)
    """
    try:
        if provider == "aws":
            import boto3
            if resource_type == "ec2":
                ec2 = boto3.client("ec2")
                instances = ec2.describe_instances()
                return json.dumps({
                    "instances": str(instances)[:1000],
                })
            else:
                return json.dumps({"error": f"Resource type {resource_type} not implemented"})

        elif provider == "gcp":
            return json.dumps({
                "message": "GCP info requires google-cloud-compute SDK",
                "example": "List compute instances: gcloud compute instances list",
            })

        elif provider == "azure":
            return json.dumps({
                "message": "Azure info requires azure-cli and az login",
                "example": "List VMs: az vm list",
            })

        else:
            return json.dumps({"error": f"Unknown provider: {provider}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def terraform_plan(
    action: Annotated[str, "plan (dry-run) or apply (execute)"],
    directory: Annotated[str, "Directory with .tf files (default: current)"] = ".",
) -> str:
    """Plan or apply Terraform infrastructure changes.

    Always run 'plan' first to preview changes.
    """
    try:
        safe_actions = ["plan", "apply"]
        if action not in safe_actions:
            return json.dumps({"error": f"Action not allowed. Safe: {safe_actions}"})

        if action == "plan":
            result = subprocess.run(
                f"cd {directory} && terraform plan",
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return json.dumps({
                "plan": result.stdout[:3000],
                "errors": result.stderr[:1000],
            })

        elif action == "apply":
            return json.dumps({
                "message": "Apply requires interactive confirmation",
                "command": f"cd {directory} && terraform apply",
            })

    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Terraform command timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def ask_helix(
    question: Annotated[str, "Code-related question or code to review"],
) -> str:
    """Ask Helix (Code Agent) for help with code generation, review, or search.

    Use this when deploying code or needing code review before deployment.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "http://localhost:9000/tasks",
                json={"message": question},
            )
            result = response.json()
            return json.dumps({
                "agent": "helix",
                "result": result.get("content", ""),
                "status": result.get("status"),
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
async def ask_flux(
    question: Annotated[str, "Data analysis or metrics question"],
) -> str:
    """Ask Flux (Data Agent) for help with data analysis, metrics, or dashboards.

    Use this when you need to analyze logs, metrics, or performance data.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "http://localhost:9000/tasks",
                json={"message": question},
            )
            result = response.json()
            return json.dumps({
                "agent": "flux",
                "result": result.get("content", ""),
                "status": result.get("status"),
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def discover_available_agents() -> str:
    """Discover what agents are available on the platform and their capabilities.

    Use this to find out which agents can help with your task.
    """
    import httpx
    try:
        response = httpx.get("http://localhost:9000/agents")
        agents = response.json()
        summary = []
        for agent in agents:
            summary.append({
                "name": agent["name"],
                "status": agent["status"],
                "capabilities": agent.get("capabilities", [])[:3],
            })
        # Deduplicate
        unique = {a["name"]: a for a in summary}
        return json.dumps({
            "agents": list(unique.values()),
            "count": len(unique),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_tools():
    """Return list of all available tools."""
    return [
        docker_cmd,
        k8s_deploy,
        monitor_health,
        cloud_info,
        terraform_plan,
        ask_helix,
        ask_flux,
        discover_available_agents,
    ]
