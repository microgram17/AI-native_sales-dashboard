"""Visualization LlmAgent: produces a structured VisualizationPlan."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.schemas.visualization import VisualizationPlan

_INSTRUCTION = """You plan visualizations for analytics results.

User question: {user_message}
Successful results (JSON, each with a call_id): {successful_results_json}

Choose zero or more visualization specs based on both the question and the shape
of the data. Allowed types: metric_cards, bar_chart, line_chart, table. Set each
spec's 'dataset' to the call_id of the result it visualizes. For a ranking, a
bar_chart of the ranked entities is usually appropriate; winner KPIs can be
metric_cards. If there are no results, return an empty list.
Return a VisualizationPlan.
"""


def build_visualization_agent(model: LiteLlm) -> LlmAgent:
    return LlmAgent(
        name="visualization",
        model=model,
        instruction=_INSTRUCTION,
        output_schema=VisualizationPlan,
        output_key="visualization_plan",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
