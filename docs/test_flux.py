import asyncio
import os

# Use Ollama for testing
os.environ["OMI_SUPERVISOR_MODEL"] = "ollama/llama3.2"
os.environ["OMI_ANALYST_MODEL"] = "ollama/llama3.2"

from agents.flux.flux.supervisor.graph import run

async def test():
    print("[Testing Flux Agent]")
    result = await run("Analyze the CSV file /tmp/test.csv if it exists, otherwise tell me what analysis tools you have")
    print("\nFlux Response:")
    print(result)

asyncio.run(test())
