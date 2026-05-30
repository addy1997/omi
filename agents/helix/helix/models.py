"""Multi-provider LangChain chat models for each agent role.

Model string format:  <provider>/<model-id>
  anthropic/claude-sonnet-4-5
  openai/gpt-4o
  openai/gpt-4o-mini
  ollama/llama3.2          (local)

Provider is inferred from the prefix; the right LangChain integration is used.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from .config import settings


def _make(model_str: str) -> BaseChatModel:
    """Return the appropriate LangChain chat model for the given model string."""
    provider, _, model_id = model_str.partition("/")
    model_id = model_id or model_str   # handle bare model names

    if provider in ("anthropic", "claude"):
        from langchain_anthropic import ChatAnthropic  # type: ignore
        return ChatAnthropic(
            model=model_id,
            temperature=0,
            api_key=os.getenv("ANTHROPIC_API_KEY", settings.anthropic_api_key if hasattr(settings, "anthropic_api_key") else ""),  # type: ignore[arg-type]
        )

    if provider in ("openai", "gpt"):
        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(
            model=model_id,
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY") or "placeholder",  # type: ignore[arg-type]
        )

    if provider == "ollama":
        try:
            from langchain_ollama import ChatOllama  # type: ignore
            return ChatOllama(model=model_id, temperature=0)
        except ImportError:
            from langchain_community.chat_models import ChatOllama as _ChatOllama  # type: ignore
            return _ChatOllama(model=model_id, temperature=0)

    if provider == "google" or provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        )

    # Fallback: OpenAI-compatible (works with local servers too)
    from langchain_openai import ChatOpenAI  # type: ignore
    return ChatOpenAI(model=model_str, temperature=0, api_key=os.getenv("OPENAI_API_KEY") or "placeholder")  # type: ignore[arg-type]


@lru_cache(maxsize=None)
def get_model(role: str) -> BaseChatModel:
    mapping = {
        "supervisor": settings.supervisor_model,
        "coder":      settings.coder_model,
        "explorer":   settings.explorer_model,
        "planner":    settings.planner_model,
        "researcher": settings.researcher_model,
        "triager":    settings.triager_model,
    }
    return _make(mapping.get(role, settings.coder_model))
