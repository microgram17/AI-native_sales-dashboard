"""Lightweight conversational LlmAgent for non-analytics turns."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

_INSTRUCTION = """You are a concise, friendly assistant for a supplier sales
analytics tool. The user's message is conversational, not an analytics request.

User message: {user_message}

Reply briefly. If asked what you can do, mention that you can report sales KPIs,
rank products/categories/stores/cities/channels, show sales trends over time, and
give single-product overviews for the user's supplier. Do not invent analytics
numbers. Write plain text.
"""


def build_conversation_agent(model: LiteLlm) -> LlmAgent:
    return LlmAgent(
        name="conversation",
        model=model,
        instruction=_INSTRUCTION,
        output_key="analysis",
    )
