
"""Lightweight conversational LLM for non-analytics turns."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm


_INSTRUCTION = """You are a concise assistant for a supplier sales analytics tool.
The user's message is conversational rather than an analytics request.

User message: {user_message}
UI language: {ui_language}

The UI language is authoritative:
- ui_language="sv" -> reply in natural Swedish.
- ui_language="en" -> reply in natural English.

If asked what you can do, mention sales KPI summaries, rankings by
product/category/store/city/channel, time trends, product overviews and
visualizations. Do not invent analytics numbers.

Reply briefly in plain text.
"""


def build_conversation_agent(
    model: LiteLlm,
) -> LlmAgent:
    return LlmAgent(
        name="conversation",
        model=model,
        instruction=_INSTRUCTION,
        output_key="analysis",
    )
