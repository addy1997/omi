"""Documentation tools for Lumen agent."""
import ast
import json
import subprocess
from typing import Annotated

from langchain_core.tools import tool

from ..config import settings


@tool
def extract_api_surface(
    source_path: Annotated[str, "Path to the source file to document"],
) -> str:
    """Parse a Python source file and return its public API: functions and classes
    with signatures and existing docstrings. Grounds doc generation in real code."""
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return json.dumps({"error": f"cannot read/parse {source_path}: {e}"})

    surface = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            surface.append({
                "kind": "function",
                "name": node.name,
                "args": [a.arg for a in node.args.args],
                "has_docstring": ast.get_docstring(node) is not None,
            })
        elif isinstance(node, ast.ClassDef):
            surface.append({
                "kind": "class",
                "name": node.name,
                "methods": [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ],
                "has_docstring": ast.get_docstring(node) is not None,
            })
    return json.dumps({"source": source_path, "api": surface, "count": len(surface)})


@tool
def check_doc_coverage(
    source_path: Annotated[str, "Source file to check for missing docstrings"],
) -> str:
    """Report which public modules/functions/classes lack docstrings, and the
    docstring coverage percentage against the configured threshold."""
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return json.dumps({"error": str(e)})

    total = documented = 0
    missing = []
    if not ast.get_docstring(tree):
        missing.append("<module>")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            total += 1
            if ast.get_docstring(node):
                documented += 1
            else:
                missing.append(node.name)

    pct = (documented / total * 100) if total else 100.0
    return json.dumps({
        "source": source_path,
        "documented": documented,
        "total": total,
        "coverage_percent": round(pct, 1),
        "threshold": settings.doc_coverage_threshold,
        "meets_threshold": pct >= settings.doc_coverage_threshold,
        "missing": missing,
        "style": settings.docstring_style,
    })


@tool
def generate_changelog(
    since: Annotated[str, "Git ref/tag to start from, e.g. 'v0.1.0' or 'HEAD~20'"] = "HEAD~20",
    repo_dir: Annotated[str, "Repository directory"] = ".",
) -> str:
    """Collect commit subjects since a ref so the agent can group them into a
    Keep-a-Changelog style entry (Added/Changed/Fixed/Removed)."""
    try:
        result = subprocess.run(
            f"git -C {repo_dir} log {since}..HEAD --pretty=format:%s",
            shell=True, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return json.dumps({"error": result.stderr[:500] or "git log failed"})
        commits = [c for c in result.stdout.splitlines() if c.strip()]
        return json.dumps({"since": since, "commit_count": len(commits), "commits": commits})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def read_project_context(
    repo_dir: Annotated[str, "Repository directory"] = ".",
) -> str:
    """Read grounding files (pyproject.toml/package.json and any existing README)
    so generated docs match project name, deps, and prior conventions."""
    import os
    ctx = {}
    for fname in ("pyproject.toml", "package.json", "README.md", "README.rst"):
        path = os.path.join(repo_dir, fname)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    ctx[fname] = f.read()[:3000]
            except OSError:
                pass
    return json.dumps({"found": list(ctx.keys()), "context": ctx})


@tool
async def ask_helix(
    question: Annotated[str, "Implementation detail you need to document accurately"],
) -> str:
    """Ask Helix (Code Agent) for implementation details to document correctly."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "http://localhost:9000/tasks",
                json={"message": question, "metadata": {"capability": "code_search"}},
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
def discover_available_agents() -> str:
    """Discover what agents are available on the platform and their capabilities."""
    import httpx
    try:
        response = httpx.get("http://localhost:9000/agents")
        agents = response.json()
        unique = {a["name"]: {
            "name": a["name"], "status": a["status"],
            "capabilities": a.get("capabilities", [])[:3],
        } for a in agents}
        return json.dumps({"agents": list(unique.values()), "count": len(unique)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_tools():
    """Return list of all available tools."""
    return [
        extract_api_surface,
        check_doc_coverage,
        generate_changelog,
        read_project_context,
        ask_helix,
        discover_available_agents,
    ]
