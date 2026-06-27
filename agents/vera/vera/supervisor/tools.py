"""Testing/QA tools for Vera agent."""
import ast
import json
import subprocess
from typing import Annotated

from langchain_core.tools import tool

from ..config import settings


@tool
def generate_unit_tests(
    source_path: Annotated[str, "Path to the source file under test"],
    framework: Annotated[str, "Test framework: pytest, unittest"] = "pytest",
) -> str:
    """Analyze a Python source file and return its public functions/classes plus a
    test skeleton (one parametrized test stub per callable) for the given framework.

    The LLM fills in assertions; this guarantees the structure and naming are correct
    and that no public callable is missed.
    """
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
    except (OSError, SyntaxError) as e:
        return json.dumps({"error": f"cannot read/parse {source_path}: {e}"})

    targets = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args if a.arg != "self"]
            targets.append({"kind": "function", "name": node.name, "args": args})
        elif isinstance(node, ast.ClassDef):
            targets.append({"kind": "class", "name": node.name, "args": []})

    module = source_path.replace("/", ".").rstrip(".py").strip(".")
    lines = [f"import pytest", f"# from {module} import ...", ""]
    for t in targets:
        safe = t["name"]
        lines += [
            f"@pytest.mark.parametrize('case', [])  # TODO: fill cases",
            f"def test_{safe}_behaviour(case):",
            f"    # arrange / act / assert for {t['kind']} {safe}",
            f"    raise NotImplementedError",
            "",
        ]
    return json.dumps({
        "source": source_path,
        "framework": framework,
        "targets": targets,
        "skeleton": "\n".join(lines),
    })


@tool
def run_tests(
    path: Annotated[str, "Test file or directory to run"] = ".",
    extra_args: Annotated[str, "Extra pytest args, e.g. '-k login -x'"] = "",
) -> str:
    """Run pytest and return parsed pass/fail/error counts plus the tail of output."""
    try:
        cmd = f"{settings.test_framework} {path} {extra_args} -q --no-header"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=settings.test_timeout_s
        )
        out = result.stdout + result.stderr
        return json.dumps({
            "command": cmd,
            "returncode": result.returncode,
            "passed": result.returncode == 0,
            "tail": out[-2500:],
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"tests timed out after {settings.test_timeout_s}s"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def analyze_coverage(
    path: Annotated[str, "Package/module to measure coverage for"] = ".",
    test_path: Annotated[str, "Tests to run while measuring"] = ".",
) -> str:
    """Run coverage over the test suite and report total percent vs the configured
    threshold, plus the files with the lowest coverage."""
    try:
        run = subprocess.run(
            f"coverage run -m {settings.test_framework} {test_path} -q",
            shell=True, capture_output=True, text=True, timeout=settings.test_timeout_s,
        )
        report = subprocess.run(
            "coverage report", shell=True, capture_output=True, text=True, timeout=30
        )
        total = None
        for line in report.stdout.splitlines():
            if line.startswith("TOTAL"):
                for tok in line.split():
                    if tok.endswith("%"):
                        total = float(tok.rstrip("%"))
        return json.dumps({
            "total_percent": total,
            "threshold": settings.coverage_threshold,
            "meets_threshold": (total is not None and total >= settings.coverage_threshold),
            "report": report.stdout[-2000:],
            "run_errors": run.stderr[-500:],
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "coverage run timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def detect_test_gaps(
    source_path: Annotated[str, "Source file to scan for untested public callables"],
) -> str:
    """Static scan: list public functions/classes in a source file so the agent can
    cross-check them against existing tests and flag gaps. No execution required."""
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError) as e:
        return json.dumps({"error": str(e)})

    public = [
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not n.name.startswith("_")
    ]
    return json.dumps({"source": source_path, "public_symbols": public, "count": len(public)})


@tool
def generate_fixtures(
    dependency: Annotated[str, "What to mock/fixture, e.g. 'httpx client', 'db session'"],
    framework: Annotated[str, "pytest or unittest"] = "pytest",
) -> str:
    """Return a fixture/mock template for a dependency so tests stay isolated and
    deterministic. The agent customizes the returned skeleton."""
    if framework == "pytest":
        tmpl = (
            "import pytest\n"
            "from unittest.mock import MagicMock\n\n"
            "@pytest.fixture\n"
            f"def mock_{dependency.split()[0]}():\n"
            "    m = MagicMock()\n"
            "    # configure return values / side effects here\n"
            "    yield m\n"
        )
    else:
        tmpl = (
            "from unittest.mock import MagicMock, patch\n\n"
            f"# patch('module.{dependency.split()[0]}') in setUp\n"
        )
    return json.dumps({"dependency": dependency, "framework": framework, "template": tmpl})


@tool
async def ask_helix(
    question: Annotated[str, "Code-related question or request for source under test"],
) -> str:
    """Ask Helix (Code Agent) for source context or implementation details."""
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
        generate_unit_tests,
        run_tests,
        analyze_coverage,
        detect_test_gaps,
        generate_fixtures,
        ask_helix,
        discover_available_agents,
    ]
