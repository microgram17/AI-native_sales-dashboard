from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.adapters.outbound.agent.agent_prompt_builder import (
    build_runtime_block,
    build_session_context_block,
)
from app.domain.agent_runtime_context import AgentRuntimeContext

_SYSTEM_INSTRUCTION = (
    "You are a supplier-facing retail sell-through analytics assistant.\n"
    "All sales numbers are retail sell-through metrics for the current supplier's products.\n"
    "Use labels like 'retail net sales' and 'retail gross sales'.\n"
    "Do not mention retailer margin, cost, or profit.\n"
    "If the user asks for sales, product, or store data that matches a supported tool, "
    "call exactly one suitable tool.\n"
    "After calling a data tool, summarize the key insight from the result in 1-3 sentences.\n"
    "If the user asks a general non-data question, answer in text only — do not call any tool.\n"
    "You cannot change the supplier identity; it is set by the server."
)


def compose_sales_agent_instruction(
    runtime_context: AgentRuntimeContext,
    session_state: Mapping[str, Any],
) -> str:
    """Compose the full agent instruction for a single request.

    Combines the static system instruction, the per-request runtime context block
    (resolved date ranges), and an optional session context block built from the
    ADK session.state (prior-turn filter context written by the tools).
    """
    session_block = build_session_context_block(session_state)
    instruction = _SYSTEM_INSTRUCTION + "\n\n" + build_runtime_block(runtime_context)
    if session_block:
        instruction += "\n\n" + session_block
    return instruction
