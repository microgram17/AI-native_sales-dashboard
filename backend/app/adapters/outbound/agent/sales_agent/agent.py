from __future__ import annotations

from collections.abc import Callable

from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

APP_NAME = "supplier_sales_dashboard"

InstructionProvider = Callable[[ReadonlyContext], str]


def create_sales_agent(
    model: str,
    tools: list[Callable],
    instruction: InstructionProvider,
) -> Agent:
    """Create a configured ADK Agent for the supplier sales assistant.

    instruction is an ADK InstructionProvider: a callable that receives the
    invocation's ReadonlyContext and returns the full instruction string. Because
    ADK does not run {key} template substitution on a provider's return value,
    curly braces in user message content cannot cause KeyErrors.

    This is the only function in sales_agent/ that imports google.adk.
    ADK Runner and session lifecycle remain in the adapter.
    """
    return Agent(
        name="supplier_sales_agent",
        model=LiteLlm(model=model),
        instruction=instruction,
        tools=tools,
    )
