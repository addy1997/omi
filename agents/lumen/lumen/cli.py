"""Lumen CLI — Documentation agent command interface."""
import asyncio
import typer
from rich.console import Console

app = typer.Typer(name="lumen", help="Lumen — Documentation agent")
console = Console()


@app.command(name="serve-agent")
def serve_agent(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8005, "--port", "-p"),
    platform_url: str = typer.Option(None, "--platform", "-P"),
):
    """Start Lumen as a registered platform agent."""
    from .platform_adapter import run_agent_server
    asyncio.run(run_agent_server(host=host, port=port, platform_url=platform_url))


@app.command()
def chat(session: str = typer.Option(None, "--session", "-s")):
    """Start interactive chat with Lumen."""
    console.print("[bold green]Lumen[/bold green] — Documentation Agent", style="bold")
    console.print("Capabilities: Docstrings, READMEs, API reference, architecture docs, changelogs")
    console.print("[dim]Running in standalone mode. Connect to platform: lumen serve-agent --platform http://localhost:9000[/dim]")


if __name__ == "__main__":
    app()
