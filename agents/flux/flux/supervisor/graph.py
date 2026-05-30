"""Flux supervisor — LangGraph orchestration for data tasks."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

_FLUX_SYSTEM = """You are Flux, a data analysis specialist agent.

Your job is to handle data exploration, SQL generation, analytics, and BI.

CAPABILITIES
- SQL generation and execution (PostgreSQL, DuckDB, BigQuery)
- Data exploration and profiling
- Statistical analysis and correlation detection
- Data visualization (Plotly charts, dashboards)
- ETL pipeline construction
- CSV/Parquet file analysis
- Query optimization
- BI tool integration (Tableau, Looker, Metabase)

ROUTING RULES
1. If the user wants SQL analysis → generate and execute queries
2. If the user needs data visualization → create interactive charts
3. If the user wants ETL setup → design data pipelines
4. If the user needs statistical analysis → perform analysis
5. Otherwise → summarize what you'd do

Always verify data accuracy and validate query results."""

_system_msg = SystemMessage(content=_FLUX_SYSTEM)
_parser = JsonOutputParser()

async def run(
    message: str,
    session_id: str | None = None,
) -> str:
    """Run Flux supervisor for a data task."""
    from ..config import settings

    return f"""[Flux] Data Analysis Task: {message}

Capabilities available:
• SQL generation & execution
• Data exploration & profiling
• Statistical analysis
• Data visualization (Plotly)
• ETL pipeline design
• File analysis (CSV/Parquet)
• BI integration
• Query optimization

Status: Ready to handle data analysis tasks.
Connect to platform at http://localhost:9000 to submit tasks."""
