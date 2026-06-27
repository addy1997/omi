"""File-system tools: read, write, edit, grep, find, ls.

All paths are validated to stay within the configured repos dir.
Read-only mode disables write/edit operations (used by Explorer, Planner, Triager).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool

from ..config import settings


def _safe_path(repo: str, rel_path: str) -> Path:
    base = (settings.repos_dir / repo).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path escape detected: {rel_path}")
    return target


# ── Read ────────────────────────────────────────────────────


@tool
def read_file(
    repo: Annotated[str, "Repository name (directory under repos_dir)"],
    path: Annotated[str, "File path relative to repo root"],
    start_line: Annotated[int, "First line to read (1-indexed, 0 = start)"] = 0,
    end_line: Annotated[int, "Last line to read (0 = EOF)"] = 0,
) -> str:
    """Read a file from the repository. Optionally slice by line range."""
    target = _safe_path(repo, path)
    if not target.exists():
        return f"ERROR: {path} not found in {repo}"
    lines = target.read_text(errors="replace").splitlines(keepends=True)
    if start_line or end_line:
        s = max(0, start_line - 1)
        e = end_line if end_line else len(lines)
        lines = lines[s:e]
    content = "".join(lines)
    if len(content) > 40_000:
        content = content[:40_000] + "\n... [truncated]"
    return content


@tool
def grep(
    repo: Annotated[str, "Repository name"],
    pattern: Annotated[str, "Regex pattern to search for"],
    path: Annotated[str, "Sub-path to restrict search (empty = whole repo)"] = "",
    case_sensitive: Annotated[bool, "Case-sensitive match"] = True,
    max_results: Annotated[int, "Maximum number of matching lines to return"] = 50,
) -> str:
    """Search for a regex pattern across all files in the repository."""
    base = _safe_path(repo, path) if path else settings.repos_dir / repo
    flags = 0 if case_sensitive else re.IGNORECASE
    results: list[str] = []
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"ERROR: invalid regex — {e}"

    for file in sorted(base.rglob("*")):
        if not file.is_file():
            continue
        if any(p in file.parts for p in (".git", "node_modules", "__pycache__", ".venv")):
            continue
        try:
            for i, line in enumerate(file.read_text(errors="replace").splitlines(), 1):
                if regex.search(line):
                    rel = file.relative_to(settings.repos_dir / repo)
                    results.append(f"{rel}:{i}: {line.rstrip()}")
                    if len(results) >= max_results:
                        return "\n".join(results) + f"\n... (stopped at {max_results} results)"
        except Exception:
            continue
    return "\n".join(results) if results else "No matches found."


@tool
def find_files(
    repo: Annotated[str, "Repository name"],
    pattern: Annotated[str, "Glob pattern, e.g. '*.py' or 'test_*.py'"],
    path: Annotated[str, "Sub-path to restrict search (empty = whole repo)"] = "",
) -> str:
    """Find files matching a glob pattern in the repository."""
    base = _safe_path(repo, path) if path else settings.repos_dir / repo
    matches = [
        str(f.relative_to(settings.repos_dir / repo))
        for f in sorted(base.rglob(pattern))
        if f.is_file() and ".git" not in f.parts
    ]
    if not matches:
        return "No files found."
    return "\n".join(matches[:200])


@tool
def list_dir(
    repo: Annotated[str, "Repository name"],
    path: Annotated[str, "Directory path relative to repo root (empty = root)"] = "",
) -> str:
    """List contents of a directory in the repository."""
    target = _safe_path(repo, path) if path else settings.repos_dir / repo
    if not target.exists():
        return f"ERROR: {path or '/'} not found"
    if not target.is_dir():
        return f"ERROR: {path} is a file, not a directory"
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = []
    for e in entries[:100]:
        if e.name.startswith(".") and e.name != ".github":
            continue
        suffix = "/" if e.is_dir() else ""
        lines.append(f"{'d' if e.is_dir() else 'f'}  {e.name}{suffix}")
    return "\n".join(lines) if lines else "(empty directory)"


# ── Write (Coder only) ───────────────────────────────────────


@tool
def write_file(
    repo: Annotated[str, "Repository name"],
    path: Annotated[str, "File path relative to repo root"],
    content: Annotated[str, "Full file content to write"],
    worktree: Annotated[str, "Worktree name (task branch) — must be set for write ops"] = "",
) -> str:
    """Write (create or overwrite) a file. Always use a worktree, never write on main."""
    if not worktree:
        return "ERROR: worktree must be specified for write operations."
    base = settings.worktrees_dir / repo / worktree
    if not base.exists():
        return f"ERROR: worktree '{worktree}' not found at {base}"
    target = (base / path).resolve()
    if not str(target).startswith(str(base.resolve())):
        return "ERROR: path escape detected."
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"Written {path} ({len(content.splitlines())} lines)"


@tool
def edit_file(
    repo: Annotated[str, "Repository name"],
    path: Annotated[str, "File path relative to repo root"],
    old_str: Annotated[str, "Exact string to replace (must be unique in the file)"],
    new_str: Annotated[str, "Replacement string"],
    worktree: Annotated[str, "Worktree name"] = "",
) -> str:
    """Replace an exact string in a file. More surgical than write_file."""
    if not worktree:
        return "ERROR: worktree must be specified for edit operations."
    base = settings.worktrees_dir / repo / worktree
    target = (base / path).resolve()
    if not str(target).startswith(str(base.resolve())):
        return "ERROR: path escape detected."
    if not target.exists():
        return f"ERROR: {path} not found"
    content = target.read_text()
    count = content.count(old_str)
    if count == 0:
        return "ERROR: old_str not found in file."
    if count > 1:
        return f"ERROR: old_str found {count} times — make it more specific."
    target.write_text(content.replace(old_str, new_str, 1))
    return f"Edited {path} — replaced 1 occurrence."


# ── Exported tool sets ───────────────────────────────────────

READ_ONLY_TOOLS = [read_file, grep, find_files, list_dir]
ALL_TOOLS = READ_ONLY_TOOLS + [write_file, edit_file]
