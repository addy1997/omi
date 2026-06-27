"""Data analysis tools for Flux agent."""
from typing import Annotated, Any
from langchain_core.tools import tool
import json
import pandas as pd
import numpy as np


@tool
def sql_query(
    query: Annotated[str, "SQL query to execute (SELECT only)"],
    database: Annotated[str, "Database: duckdb, postgres, or bigquery"] = "duckdb",
    limit: Annotated[int, "Max rows to return (default 100)"] = 100,
) -> str:
    """Execute SQL query on configured database.

    Safe for SELECT queries only. Returns JSON results.
    """
    try:
        # Prevent write operations
        if any(keyword in query.upper() for keyword in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER"]):
            return json.dumps({"error": "Only SELECT queries allowed"})

        if database == "duckdb":
            import duckdb
            conn = duckdb.connect(":memory:")
            result = conn.execute(query + f" LIMIT {limit}").fetchall()
            columns = [desc[0] for desc in conn.description] if conn.description else []
            return json.dumps({
                "columns": columns,
                "rows": result,
                "count": len(result),
            })

        elif database == "postgres":
            return json.dumps({
                "error": "PostgreSQL not configured. Use DuckDB for local analysis."
            })

        else:
            return json.dumps({"error": f"Unknown database: {database}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def analyze_csv(
    file_path: Annotated[str, "Path to CSV or Parquet file"],
) -> str:
    """Analyze CSV/Parquet file — profile columns, detect patterns, suggest optimizations.

    Returns column stats, data types, nulls, unique values, etc.
    """
    try:
        import pandas as pd

        # Load file
        if file_path.endswith(".parquet"):
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)

        # Profile
        profile = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "nulls": df.isnull().sum().to_dict(),
            "duplicates": int(df.duplicated().sum()),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            "sample": df.head(3).to_dict(),
        }

        return json.dumps(profile)

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def generate_sample_data(
    dataset_type: Annotated[str, "Type: sales, weather, website_traffic, inventory, customer_activity"],
    num_records: Annotated[int, "Number of records to generate (default 100)"] = 100,
    num_months: Annotated[int, "For time-series: number of months (default 12)"] = 12,
) -> str:
    """Generate sample datasets for analysis and visualization.

    Supports: sales, weather, website_traffic, inventory, customer_activity.
    Returns data as JSON with columns and rows.
    """
    try:
        if dataset_type == "sales":
            dates = pd.date_range(start="2023-01-01", periods=num_months, freq="D")
            np.random.seed(42)
            data = {
                "date": dates.strftime("%Y-%m-%d").tolist(),
                "revenue": np.random.randint(500, 5000, len(dates)).tolist(),
                "orders": np.random.randint(10, 100, len(dates)).tolist(),
                "customers": np.random.randint(5, 50, len(dates)).tolist(),
                "region": np.random.choice(["US", "EU", "ASIA"], len(dates)).tolist(),
            }
            df = pd.DataFrame(data)

        elif dataset_type == "website_traffic":
            dates = pd.date_range(start="2023-01-01", periods=num_months, freq="D")
            np.random.seed(42)
            data = {
                "date": dates.strftime("%Y-%m-%d").tolist(),
                "visits": np.random.randint(1000, 50000, len(dates)).tolist(),
                "bounce_rate": np.random.uniform(0.3, 0.7, len(dates)).tolist(),
                "avg_session_duration": np.random.uniform(2, 10, len(dates)).tolist(),
                "conversion_rate": np.random.uniform(0.01, 0.05, len(dates)).tolist(),
            }
            df = pd.DataFrame(data)

        elif dataset_type == "inventory":
            products = ["SKU_001", "SKU_002", "SKU_003", "SKU_004", "SKU_005"]
            np.random.seed(42)
            data = {
                "product": (products * (num_records // len(products) + 1))[:num_records],
                "quantity": np.random.randint(10, 500, num_records).tolist(),
                "reorder_level": np.random.randint(20, 100, num_records).tolist(),
                "unit_cost": np.random.uniform(10, 500, num_records).round(2).tolist(),
            }
            df = pd.DataFrame(data)

        else:
            return json.dumps({"error": f"Unknown dataset type: {dataset_type}"})

        return json.dumps({
            "type": dataset_type,
            "rows": df.head(10).to_dict(orient="records"),
            "total_rows": len(df),
            "columns": list(df.columns),
            "data_records": df.to_dict(orient="records"),
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def generate_chart(
    data: Annotated[Any, "Data: list of dicts, or DataFrame, or JSON string"],
    chart_type: Annotated[str, "bar, line, scatter, pie, area, histogram, box"] = "line",
    x_column: Annotated[str, "Column name for X axis"] = "x",
    y_column: Annotated[str, "Column name for Y axis"] = "y",
    title: Annotated[str, "Chart title"] = "Data Visualization",
    color_by: Annotated[str, "Optional: column to color by"] = None,
) -> str:
    """Generate interactive Plotly chart from data.

    Handles multiple formats: list of dicts, JSON string, or DataFrame.
    Returns HTML embed code and preview URL.
    """
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        # Parse data
        if isinstance(data, str):
            data = json.loads(data)

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            return json.dumps({"error": f"Unsupported data type: {type(data)}"})

        # Validate columns exist
        if x_column not in df.columns or y_column not in df.columns:
            available = list(df.columns)
            return json.dumps({
                "error": f"Columns '{x_column}' or '{y_column}' not found. Available: {available}"
            })

        # Create chart based on type
        if chart_type == "line":
            fig = px.line(df, x=x_column, y=y_column, color=color_by if color_by in df.columns else None,
                         title=title, markers=True)
        elif chart_type == "bar":
            fig = px.bar(df, x=x_column, y=y_column, color=color_by if color_by in df.columns else None,
                        title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_column, y=y_column, color=color_by if color_by in df.columns else None,
                            title=title, size=y_column if y_column in df.columns else None)
        elif chart_type == "area":
            fig = px.area(df, x=x_column, y=y_column, color=color_by if color_by in df.columns else None,
                         title=title)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x_column, y=y_column, nbins=30, title=title)
        elif chart_type == "box":
            fig = px.box(df, x=x_column, y=y_column, color=color_by if color_by in df.columns else None,
                        title=title)
        else:
            return json.dumps({"error": f"Unknown chart type: {chart_type}"})

        # Enhanced layout
        fig.update_layout(
            template="plotly_white",
            height=500,
            hovermode="x unified",
            font=dict(family="Arial, sans-serif", size=12),
        )

        html = fig.to_html(include_plotlyjs='cdn', div_id=f"chart_{chart_type}")

        return json.dumps({
            "success": True,
            "type": chart_type,
            "title": title,
            "x_column": x_column,
            "y_column": y_column,
            "rows_used": len(df),
            "html": html,
            "message": f"✓ Generated {chart_type} chart with {len(df)} data points",
        })

    except Exception as e:
        return json.dumps({"error": str(e), "success": False})


@tool
def web_search(
    query: Annotated[str, "Search query for datasets or documentation"],
) -> str:
    """Search web for public datasets and data documentation.

    Returns top 5 results with links.
    """
    try:
        # Use DuckDuckGo for search
        from duckduckgo_search import DDGS

        ddgs = DDGS()
        results = ddgs.text(query, max_results=5)

        return json.dumps({
            "query": query,
            "results": results,
            "count": len(results),
        })

    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})


@tool
async def ask_helix(
    question: Annotated[str, "Code-related question or code to review"],
) -> str:
    """Ask Helix (Code Agent) for help with code generation, review, or search.

    Use this when you need code help, code review, or to search the codebase.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "http://localhost:9000/tasks",
                json={"message": question},
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
async def ask_nexus(
    question: Annotated[str, "DevOps/Infrastructure question or task"],
) -> str:
    """Ask Nexus (DevOps Agent) for help with infrastructure, deployments, Kubernetes.

    Use this when you need DevOps help, cloud operations, or infrastructure setup.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "http://localhost:9000/tasks",
                json={"message": question},
            )
            result = response.json()
            return json.dumps({
                "agent": "nexus",
                "result": result.get("content", ""),
                "status": result.get("status"),
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def discover_available_agents() -> str:
    """Discover what agents are available on the platform and their capabilities.

    Use this to find out which agents can help with your task.
    """
    import httpx
    try:
        response = httpx.get("http://localhost:9000/agents")
        agents = response.json()
        summary = []
        for agent in agents:
            summary.append({
                "name": agent["name"],
                "status": agent["status"],
                "capabilities": agent.get("capabilities", [])[:3],
            })
        # Deduplicate
        unique = {a["name"]: a for a in summary}
        return json.dumps({
            "agents": list(unique.values()),
            "count": len(unique),
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_tools():
    """Return list of all available tools."""
    return [
        sql_query,
        analyze_csv,
        generate_sample_data,
        generate_chart,
        web_search,
        ask_helix,
        ask_nexus,
        discover_available_agents,
    ]
