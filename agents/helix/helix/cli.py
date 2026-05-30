"""Helix CLI — interactive shell and server launcher."""
from __future__ import annotations

import asyncio
import uuid

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

app = typer.Typer(name="helix", help="Helix — coding agent")
console = Console()


@app.command()
def chat(
    session: str = typer.Option(None, "--session", "-s", help="Session ID to continue"),
):
    """Start an interactive chat session with Omi."""
    asyncio.run(_chat_loop(session))


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload"),
):
    """Start the Omi API server."""
    import uvicorn
    uvicorn.run("helix.api.main:app", host=host, port=port, reload=reload)


@app.command(name="serve-agent")
def serve_agent(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    platform_url: str = typer.Option(None, "--platform", "-P", help="Platform URL to register with"),
):
    """Start Omi as a registered agent on the platform."""
    from .platform_adapter import run_agent_server
    asyncio.run(run_agent_server(host=host, port=port, platform_url=platform_url))


@app.command()
def history(
    session: str = typer.Argument(..., help="Session ID"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Print message history for a session."""
    asyncio.run(_print_history(session, limit))


@app.command()
def learn(
    name: str = typer.Argument(...),
    body: str = typer.Argument(...),
    category: str = typer.Option("convention", "--category", "-c"),
    repo: str = typer.Option(None, "--repo", "-r"),
):
    """Add an entry to the shared knowledge base."""
    asyncio.run(_add_learning(name, body, category, repo))


# ── Async implementations ─────────────────────────────────────

async def _chat_loop(session_id: str | None):
    from .memory.session import init_db
    from .supervisor.graph import run as omi_run

    await init_db()
    sid = session_id or str(uuid.uuid4())

    console.print(Panel(
        "[bold green]Helix[/bold blue] — multi-agent coding platform\n"
        f"Session: [dim]{sid}[/dim]\n"
        "Type [bold]exit[/bold] or [bold]quit[/bold] to leave.",
        expand=False,
    ))

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if user_input.strip().lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if not user_input.strip():
            continue

        with console.status("[bold blue]Omi is thinking…[/bold blue]"):
            try:
                response = await omi_run(user_input, session_id=sid)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

        console.print(Panel(
            Markdown(response),
            title="[bold green]Helix[/bold blue]",
            border_style="blue",
            expand=False,
        ))


async def _print_history(session_id: str, limit: int):
    from .memory.session import init_db, get_history
    await init_db()
    history = await get_history(session_id, limit=limit)
    for msg in history:
        role = msg["role"].upper()
        color = "cyan" if role == "USER" else "blue"
        console.print(f"[bold {color}]{role}[/bold {color}]: {msg['content'][:200]}")


async def _add_learning(name: str, body: str, category: str, repo: str | None):
    from .memory.session import init_db
    from .memory.knowledge import add_learning
    await init_db()
    result = await add_learning(name=name, body=body, category=category, repo=repo)
    console.print(f"[green]{result}[/green]")


if __name__ == "__main__":
    app()
