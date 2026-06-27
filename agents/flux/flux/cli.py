"""Flux CLI — Data agent command interface."""
import asyncio
import typer
from rich.console import Console

app = typer.Typer(name="flux", help="Flux — Data agent")
console = Console()

@app.command(name="serve-agent")
def serve_agent(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8002, "--port", "-p"),
    platform_url: str = typer.Option(None, "--platform", "-P"),
):
    """Start Flux as a registered platform agent."""
    from .platform_adapter import run_agent_server
    asyncio.run(run_agent_server(host=host, port=port, platform_url=platform_url))

@app.command()
def chat(session: str = typer.Option(None, "--session", "-s")):
    """Start interactive chat with Flux."""
    console.print("[bold cyan]Flux[/bold cyan] — Data Agent", style="bold")
    console.print("Capabilities: SQL generation, data analysis, visualization, BI integration")
    console.print("[dim]Running in standalone mode. Connect to platform: flux serve-agent --platform http://localhost:9000[/dim]")

if __name__ == "__main__":
    app()
