"""Sandboxed shell execution.

Mode = docker  → runs command in an ephemeral container with the worktree mounted.
Mode = subprocess → runs directly in the worktree (dev/fallback only).

The coder agent uses this to run tests, linters, and build scripts.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool

from ..config import settings


def _run_subprocess(command: str, cwd: Path, timeout: int) -> str:
    forbidden = ["rm -rf /", "sudo", "mkfs", ":(){:|:&};:", "dd if=/dev/zero"]
    for f in forbidden:
        if f in command:
            return f"ERROR: forbidden command pattern detected: {f!r}"
    try:
        r = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = r.stdout + r.stderr
        return out[:10_000] + "\n...(truncated)" if len(out) > 10_000 else out
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout}s"
    except Exception as e:
        return f"ERROR: {e}"


def _run_docker(command: str, cwd: Path, timeout: int) -> str:
    try:
        import docker  # type: ignore

        client = docker.from_env()
        result = client.containers.run(
            image="python:3.11-slim",
            command=["bash", "-c", command],
            volumes={str(cwd): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            remove=True,
            network_disabled=False,   # allow pip install etc.
            mem_limit="512m",
            cpu_period=100_000,
            cpu_quota=50_000,          # 50% of one CPU
            timeout=timeout,
            stderr=True,
        )
        out = result.decode() if isinstance(result, bytes) else str(result)
        return out[:10_000] + "\n...(truncated)" if len(out) > 10_000 else out
    except Exception as e:
        return f"ERROR (docker): {e} — falling back to subprocess"


@tool
def run_shell(
    repo: Annotated[str, "Repository name"],
    command: Annotated[str, "Shell command to run (e.g. 'pytest tests/', 'ruff check .')"],
    task_name: Annotated[str, "Worktree task slug — required for safety"] = "",
    timeout: Annotated[int, "Timeout in seconds (max 120)"] = 60,
) -> str:
    """Run a shell command inside a worktree. Used for tests, linting, builds."""
    timeout = min(timeout, settings.shell_timeout)
    if task_name:
        cwd = settings.worktrees_dir / repo / task_name
    else:
        cwd = settings.repos_dir / repo

    if not cwd.exists():
        return f"ERROR: working directory not found: {cwd}"

    if settings.sandbox == "docker":
        return _run_docker(command, cwd, timeout)
    return _run_subprocess(command, cwd, timeout)


ALL_TOOLS = [run_shell]
