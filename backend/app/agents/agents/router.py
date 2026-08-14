"""Request-router LlmAgent: classifies the turn before any MCP/planner work."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.schemas.agent import RouteDecision

_INSTRUCTION = """You route a user's turn in a supplier sales analytics assistant.

User message: {user_message}
Prior analytical results exist: {has_prior_results}
Concise prior context (entities/period/filters, may be empty): {prior_context_summary}

Choose exactly one route:
- new_data: answering requires a NEW analytics query. Choose this whenever the
  answer needs data not already present in prior results — a time series /
  monthly / "over time" breakdown, a different grouping or metric, a different
  entity, or a product overview. Examples: "best-selling product this year",
  "give me an overview of that product", "show its monthly sales".
- reuse_data: the SAME prior results already contain the needed numbers and the
  user just wants them re-interpreted and re-presented.
- visualization_only: the user only wants existing data shown differently
  (e.g. "show that as a bar chart").
- analysis_only: a follow-up interpretation answerable from the existing
  results alone (e.g. "which of those stands out?").
- conversation: small talk or capability questions ("thanks", "what can you do?").

When unsure whether existing results truly contain the answer, prefer new_data.
If a non-new_data route would need prior results but none exist, prefer new_data.
Never reference supplier IDs, tokens or roles. Return a RouteDecision.
"""


def build_router_agent(model: LiteLlm) -> LlmAgent:
    return LlmAgent(
        name="router",
        model=model,
        instruction=_INSTRUCTION,
        output_schema=RouteDecision,
        output_key="route_decision",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
