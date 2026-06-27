"""GitHub tools via PyGitHub — issues, PRs, code search."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from langchain_core.tools import tool

from ..config import settings


@lru_cache(maxsize=1)
def _gh():
    from github import Github  # type: ignore
    return Github(settings.github_token)


def _repo(owner_repo: str):
    return _gh().get_repo(owner_repo)


# ── Issues ───────────────────────────────────────────────────


@tool
def list_issues(
    owner_repo: Annotated[str, "owner/repo string e.g. 'octocat/Hello-World'"],
    state: Annotated[str, "open | closed | all"] = "open",
    label: Annotated[str, "Filter by label (empty = all)"] = "",
    limit: Annotated[int, "Max issues to return"] = 20,
) -> str:
    """List GitHub issues for a repository."""
    r = _repo(owner_repo)
    kwargs: dict = {"state": state}
    if label:
        kwargs["labels"] = [label]
    issues = list(r.get_issues(**kwargs))[:limit]
    if not issues:
        return "No issues found."
    lines = [f"#{i.number} [{i.state}] {i.title} — {', '.join(l.name for l in i.labels)}"
             for i in issues]
    return "\n".join(lines)


@tool
def get_issue(
    owner_repo: Annotated[str, "owner/repo"],
    number: Annotated[int, "Issue number"],
) -> str:
    """Get full details of a GitHub issue including body and comments."""
    issue = _repo(owner_repo).get_issue(number)
    comments = "\n---\n".join(
        f"@{c.user.login}: {c.body}" for c in issue.get_comments()
    )
    return (
        f"#{issue.number} {issue.title}\n"
        f"State: {issue.state} | Labels: {', '.join(l.name for l in issue.labels)}\n"
        f"Author: @{issue.user.login}\n\n{issue.body or '(no body)'}\n\n"
        f"--- Comments ---\n{comments or '(none)'}"
    )


@tool
def create_issue(
    owner_repo: Annotated[str, "owner/repo"],
    title: Annotated[str, "Issue title"],
    body: Annotated[str, "Issue body (markdown)"],
    labels: Annotated[str, "Comma-separated labels e.g. 'bug,enhancement'"] = "",
) -> str:
    """Create a new GitHub issue."""
    r = _repo(owner_repo)
    label_list = [l.strip() for l in labels.split(",") if l.strip()]
    issue = r.create_issue(title=title, body=body, labels=label_list or [])
    return f"Created issue #{issue.number}: {issue.html_url}"


@tool
def comment_on_issue(
    owner_repo: Annotated[str, "owner/repo"],
    number: Annotated[int, "Issue number"],
    body: Annotated[str, "Comment body (markdown)"],
) -> str:
    """Post a comment on a GitHub issue."""
    issue = _repo(owner_repo).get_issue(number)
    comment = issue.create_comment(body)
    return f"Comment posted: {comment.html_url}"


@tool
def label_issue(
    owner_repo: Annotated[str, "owner/repo"],
    number: Annotated[int, "Issue number"],
    labels: Annotated[str, "Comma-separated labels to add"],
) -> str:
    """Add labels to a GitHub issue."""
    issue = _repo(owner_repo).get_issue(number)
    label_list = [l.strip() for l in labels.split(",") if l.strip()]
    issue.add_to_labels(*label_list)
    return f"Added labels {label_list} to #{number}"


@tool
def close_issue(
    owner_repo: Annotated[str, "owner/repo"],
    number: Annotated[int, "Issue number"],
    reason: Annotated[str, "Brief reason for closing"] = "",
) -> str:
    """Close a GitHub issue (optionally with a comment)."""
    issue = _repo(owner_repo).get_issue(number)
    if reason:
        issue.create_comment(f"Closing: {reason}")
    issue.edit(state="closed")
    return f"Closed issue #{number}"


# ── Pull Requests ─────────────────────────────────────────────


@tool
def list_prs(
    owner_repo: Annotated[str, "owner/repo"],
    state: Annotated[str, "open | closed | all"] = "open",
    limit: Annotated[int, "Max PRs to return"] = 20,
) -> str:
    """List pull requests for a repository."""
    prs = list(_repo(owner_repo).get_pulls(state=state))[:limit]
    if not prs:
        return "No PRs found."
    return "\n".join(
        f"#{p.number} [{p.state}] {p.title} ({p.head.ref} → {p.base.ref})" for p in prs
    )


@tool
def get_pr(
    owner_repo: Annotated[str, "owner/repo"],
    number: Annotated[int, "PR number"],
) -> str:
    """Get full details of a pull request including changed files."""
    pr = _repo(owner_repo).get_pull(number)
    files = "\n".join(f"  {f.filename} (+{f.additions} -{f.deletions})"
                      for f in pr.get_files())
    return (
        f"#{pr.number} {pr.title}\n"
        f"State: {pr.state} | {pr.head.ref} → {pr.base.ref}\n"
        f"Author: @{pr.user.login}\n\n{pr.body or '(no body)'}\n\n"
        f"--- Changed files ---\n{files}"
    )


@tool
def create_pr(
    owner_repo: Annotated[str, "owner/repo"],
    title: Annotated[str, "PR title"],
    body: Annotated[str, "PR description (markdown)"],
    head: Annotated[str, "Head branch (must be omi/*)"],
    base: Annotated[str, "Base branch to merge into"] = "main",
) -> str:
    """Open a pull request. Head branch must be an omi/* branch."""
    if not head.startswith("omi/"):
        return "ERROR: PRs may only be opened from omi/* branches."
    pr = _repo(owner_repo).create_pull(title=title, body=body, head=head, base=base)
    return f"Created PR #{pr.number}: {pr.html_url}"


# ── Search ────────────────────────────────────────────────────


@tool
def search_code(
    owner_repo: Annotated[str, "owner/repo"],
    query: Annotated[str, "Search query (GitHub code search syntax)"],
    limit: Annotated[int, "Max results"] = 10,
) -> str:
    """Search code in a repository using GitHub's code search."""
    results = list(_gh().search_code(f"{query} repo:{owner_repo}"))[:limit]
    if not results:
        return "No results found."
    return "\n".join(f"{r.path}:{r.repository.full_name}" for r in results)


# ── Exported tool sets ────────────────────────────────────────

READ_ONLY_TOOLS = [list_issues, get_issue, list_prs, get_pr, search_code]
ISSUE_TOOLS = READ_ONLY_TOOLS + [create_issue, comment_on_issue, label_issue, close_issue]
PR_TOOLS = READ_ONLY_TOOLS + [create_pr]
ALL_TOOLS = READ_ONLY_TOOLS + [create_issue, comment_on_issue, label_issue, close_issue, create_pr]
