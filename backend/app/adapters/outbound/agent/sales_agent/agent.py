from __future__ import annotations

from collections.abc import Callable

from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm

APP_NAME = "supplier_sales_dashboard"


def create_sales_agent(model: str, tools: list[Callable], instruction: str) -> Agent:
    """Create a configured ADK Agent for the supplier sales assistant.

    This is the only function in sales_agent/ that imports google.adk.
    ADK Runner and session lifecycle remain in the adapter.
    """
    return Agent(
        name="supplier_sales_agent",
        model=LiteLlm(model=model),
        instruction=instruction,
        tools=tools,
    )
