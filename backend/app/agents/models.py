"""Centralized ADK model configuration (LiteLLM over OpenAI)."""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm

from app.config import Settings


def build_model(settings: Settings) -> LiteLlm:
    """Return a LiteLlm model bound to the configured OpenAI model.

    The API key is taken from settings and exported for LiteLLM; it is never
    logged.
    """
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    return LiteLlm(model=f"openai/{settings.openai_model}", api_key=settings.openai_api_key)
