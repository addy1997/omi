"""Git tools: log, diff, blame, worktree management, push.

Safety rules mirrored from Coda:
  - push is only allowed on branches prefixed with  omi/
  - worktrees always live under settings.worktrees_dir
  - main / master are read-only
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool

from ..config import settings

_MAX_DIFF = 20_000  # chars


def _run(args: list[str], cwd: Path, timeout: int = 30) -> str:
    try:
        r = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        out = (r.stdout + r.stderr).strip()
        return out[:_MAX_DIFF] if len(out) > _MAX_DIFF else out
    except subprocess.TimeoutExpired:
        return "ERROR: git command timed out"
    except Exception as e:
        return f"ERROR: {e}"


def _repo_path(repo: str) -> Path:
    return settings.repos_dir / repo


def _worktree_path(repo: str, task: str) -> Path:
    return settings.worktrees_dir / repo / task


# ── Read-only ────────────────────────────────────────────────


@tool
def git_log(
    repo: Annotated[str, "Repository name"],
    n: Annotated[int, "Number of commits to show"] = 20,
    path: Annotated[str, "Restrict log to this file/dir (empty = whole repo)"] = "",
    since: Annotated[str, "ISO date string e.g. '2024-01-01' (empty = all)"] = "",
) -> str:
    """Show recent git commit history."""
    args = ["git", "log", f"-{n}", "--oneline", "--no-merges"]
    if since:
        args += [f"--since={since}"]
    if path:
        args += ["--", path]
    return _run(args, _repo_path(repo))


@tool
def git_diff(
    repo: Annotated[str, "Repository name"],
    ref1: Annotated[str, "Base ref (branch, tag, commit SHA, or 'HEAD')"] = "HEAD",
    ref2: Annotated[str, "Target ref (empty = working tree vs ref1)"] = "",
    path: Annotated[str, "Restrict diff to this file/dir"] = "",
    stat_only: Annotated[bool, "Show --stat summary only (no full diff)"] = False,
) -> str:
    """Show diff between two refs, or between a ref and the working tree."""
    args = ["git", "diff"]
    if stat_only:
        args.append("--stat")
    args.append(ref1)
    if ref2:
        args.append(ref2)
    if path:
        args += ["--", path]
    return _run(args, _repo_path(repo))


@tool
def git_blame(
    repo: Annotated[str, "Repository name"],
    path: Annotated[str, "File path relative to repo root"],
    start_line: Annotated[int, "First line (1-indexed, 0 = start)"] = 0,
    end_line: Annotated[int, "Last line (0 = EOF)"] = 0,
) -> str:
    """Show who last modified each line of a file."""
    args = ["git", "blame", "--date=short"]
    if start_line and end_line:
        args += [f"-L{start_line},{end_line}"]
    args.append(path)
    return _run(args, _repo_path(repo))


@tool
def git_show(
    repo: Annotated[str, "Repository name"],
    ref: Annotated[str, "Commit SHA, tag, or branch name"],
) -> str:
    """Show metadata and diffstat for a single commit."""
    args = ["git", "show", "--stat", "--no-patch", ref]
    return _run(args, _repo_path(repo))


@tool
def git_branches(
    repo: Annotated[str, "Repository name"],
    remote: Annotated[bool, "Include remote branches"] = False,
) -> str:
    """List git branches in the repository."""
    args = ["git", "branch", "-v"]
    if remote:
        args.append("-a")
    return _run(args, _repo_path(repo))


@tool
def repo_summary(
    repo: Annotated[str, "Repository name"],
) -> str:
    """High-level overview: current branch, recent commits, top-level structure."""
    rp = _repo_path(repo)
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], rp)
    log = _run(["git", "log", "-5", "--oneline"], rp)
    ls = "\n".join(p.name for p in sorted(rp.iterdir()) if not p.name.startswith("."))
    return f"Branch: {branch}\n\nRecent commits:\n{log}\n\nTop-level:\n{ls}"


# ── Write (Coder only) ───────────────────────────────────────


@tool
def create_worktree(
    repo: Annotated[str, "Repository name"],
    task_name: Annotated[str, "Short task slug, e.g. 'fix-auth-bug'"],
    base_ref: Annotated[str, "Branch to base the worktree on"] = "main",
) -> str:
    """Create an isolated git worktree for a coding task (branch: omi/<task_name>)."""
    rp = _repo_path(repo)
    wt = _worktree_path(repo, task_name)
    branch = f"omi/{task_name}"
    if wt.exists():
        return f"Worktree already exists at {wt}"
    wt.parent.mkdir(parents=True, exist_ok=True)
    result = _run(
        ["git", "worktree", "add", "-b", branch, str(wt), base_ref], rp, timeout=60
    )
    return f"Created worktree at {wt} on branch {branch}\n{result}"


@tool
def remove_worktree(
    repo: Annotated[str, "Repository name"],
    task_name: Annotated[str, "Task slug used in create_worktree"],
) -> str:
    """Remove a worktree and delete the associated branch."""
    rp = _repo_path(repo)
    wt = _worktree_path(repo, task_name)
    branch = f"omi/{task_name}"
    result = _run(["git", "worktree", "remove", "--force", str(wt)], rp)
    _run(["git", "branch", "-D", branch], rp)
    return f"Removed worktree {wt}\n{result}"


@tool
def git_commit(
    repo: Annotated[str, "Repository name"],
    task_name: Annotated[str, "Worktree / task slug"],
    message: Annotated[str, "Commit message (use conventional commits: feat:, fix:, etc.)"],
) -> str:
    """Stage all changes in the worktree and create a commit."""
    wt = _worktree_path(repo, task_name)
    if not wt.exists():
        return f"ERROR: worktree {task_name} not found"
    _run(["git", "add", "-A"], wt)
    return _run(["git", "commit", "-m", message], wt)


@tool
def git_push(
    repo: Annotated[str, "Repository name"],
    task_name: Annotated[str, "Worktree / task slug — branch must be omi/*"],
) -> str:
    """Push the worktree branch to origin. Only omi/* branches are allowed."""
    branch = f"omi/{task_name}"
    wt = _worktree_path(repo, task_name)
    if not wt.exists():
        return f"ERROR: worktree {task_name} not found"
    return _run(["git", "push", "-u", "origin", branch], wt, timeout=60)


# ── Exported tool sets ────────────────────────────────────────

READ_ONLY_TOOLS = [git_log, git_diff, git_blame, git_show, git_branches, repo_summary]
ALL_TOOLS = READ_ONLY_TOOLS + [create_worktree, remove_worktree, git_commit, git_push]
