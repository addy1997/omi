import asyncio
import typer
import uvicorn

app = typer.Typer(name="omi-platform", help="Omi Platform — multi-agent orchestration")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(9000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
):
    """Start the Omi platform API server."""
    uvicorn.run("omi_platform.api.main:app", host=host, port=port, reload=reload)


@app.command()
def agents():
    """List all registered agents."""
    asyncio.run(_list_agents())


async def _list_agents():
    from omi_platform.registry.store import init_registry, list_agents
    from rich.table import Table
    from rich.console import Console

    await init_registry()
    agents = await list_agents()
    console = Console()
    table = Table(title="Registered Agents")
    table.add_column("ID"); table.add_column("Name"); table.add_column("Status")
    table.add_column("Capabilities"); table.add_column("Last Heartbeat")
    for a in agents:
        table.add_row(a.id, a.name, a.status,
                      ", ".join(a.capabilities[:3]),
                      str(a.last_heartbeat)[:19])
    console.print(table)


if __name__ == "__main__":
    app()
