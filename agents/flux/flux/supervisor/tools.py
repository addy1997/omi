"""Data analysis tools for Flux agent."""
from typing import Annotated
from langchain_core.tools import tool
import json


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
def generate_chart(
    data: Annotated[list[dict], "Data points: list of dicts with x, y, label"],
    chart_type: Annotated[str, "bar, line, scatter, pie, histogram"] = "bar",
    title: Annotated[str, "Chart title"] = "Data Visualization",
) -> str:
    """Generate interactive Plotly chart.

    Returns HTML embed code for the chart.
    """
    try:
        import plotly.express as px
        import pandas as pd

        df = pd.DataFrame(data)

        if chart_type == "bar":
            fig = px.bar(df, x="label", y="value", title=title)
        elif chart_type == "line":
            fig = px.line(df, x="label", y="value", title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x="x", y="y", title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names="label", values="value", title=title)
        else:
            return json.dumps({"error": f"Unknown chart type: {chart_type}"})

        html = fig.to_html(include_plotlyjs='cdn')
        return json.dumps({
            "type": chart_type,
            "title": title,
            "html": html,
        })

    except Exception as e:
        return json.dumps({"error": str(e)})


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


def get_tools():
    """Return list of all available tools."""
    return [
        sql_query,
        analyze_csv,
        generate_chart,
        web_search,
    ]
