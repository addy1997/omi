"""Flux CLI — Data agent command interface."""
import asyncio
import typer
from rich.console import Console

app = typer.Typer(name="flux", help="Flux — Data agent")
console = Console()

@app.command()
def chat(session: str = typer.Option(None, "--session", "-s")):
    """Start interactive chat with Flux."""
    console.print("[bold cyan]Flux[/bold cyan] — Data Agent (Coming Soon)", style="bold")
    console.print("Capabilities: SQL generation, data analysis, visualization, BI integration")

@app.command()
def serve(host: str = typer.Option("0.0.0.0"), port: int = typer.Option(8002)):
    """Start Flux API server."""
    console.print(f"[yellow]Starting Flux on {host}:{port}[/yellow]")
    console.print("Data agent API server (implement with FastAPI)")

if __name__ == "__main__":
    app()
