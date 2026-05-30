"""LLM model providers for Nexus agent."""
import os
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


def _make(model_str: str):
    """Route model string to correct LangChain chat class."""
    if not model_str:
        raise ValueError("model_str required")

    # Anthropic Claude models
    if model_str.startswith("anthropic/"):
        model_name = model_str.split("/")[1]
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        return ChatAnthropic(model=model_name, api_key=api_key)

    # OpenAI models
    elif model_str.startswith("openai/"):
        model_name = model_str.split("/")[1]
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        return ChatOpenAI(model=model_name, api_key=api_key)

    # Ollama (local)
    elif model_str.startswith("ollama/"):
        from langchain_ollama import ChatOllama
        model_name = model_str.split("/")[1]
        return ChatOllama(model=model_name, base_url="http://localhost:11434")

    else:
        raise ValueError(f"Unknown model provider: {model_str}")


def get_model(role: str):
    """Get LLM for a role (supervisor, planner)."""
    from .config import settings

    if role == "supervisor":
        return _make(settings.supervisor_model)
    elif role == "planner":
        return _make(settings.planner_model)
    else:
        return _make(settings.supervisor_model)
