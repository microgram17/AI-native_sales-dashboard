
"""Deterministically assemble the stable frontend AgentQueryResponse contract."""

from __future__ import annotations

import json
import re
from typing import Any

from google.adk.agents.context import Context
from google.adk.workflow import BaseNode, node

from app.agents.answer_builder import build_short_answer
from app.agents.analysis_facts import (
    facts_have_data,
    render_analysis_facts,
)
from app.agents.request_state import coerce_request
from app.agents.state import ExecutedToolCall, StateKeys
from app.schemas.agent import (
    AgentQueryResponse,
    Dataset,
    ToolCallInfo,
)
from app.schemas.visualization import (
    VisualizationDataset,
    VisualizationPlan,
)


def _coerce_viz(
    value: Any,
) -> VisualizationPlan:
    if isinstance(value, VisualizationPlan):
        return value
    if isinstance(value, dict):
        try:
            return VisualizationPlan.model_validate(
                value
            )
        except Exception:
            return VisualizationPlan()
    if isinstance(value, str) and value.strip():
        try:
            return VisualizationPlan.model_validate_json(
                value
            )
        except Exception:
            return VisualizationPlan()
    return VisualizationPlan()


def _coerce_viz_datasets(
    value: Any,
) -> list[VisualizationDataset]:
    raw = value
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return []

    if not isinstance(raw, list):
        return []

    return [
        VisualizationDataset.model_validate(item)
        for item in raw
    ]


def _coerce_facts(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return raw if isinstance(raw, dict) else {}
    return {}


_FALSE_NO_DATA = re.compile(
    r"\b(?:no\b.{0,24}\bdata|data\b.{0,24}\b(?:unavailable|not available)|"
    r"data\b.{0,32}\b(?:not specifically (?:provided|specified)|not specified)|"
    r"no (?:specific )?results?|did not receive|"
    r"inga\b.{0,24}\bdata|data\b.{0,24}\b(?:saknas|inte tillgänglig)|"
    r"data\b.{0,32}\b(?:inte specifikt angiven|inte angiven)|"
    r"inga (?:specifika )?resultat|inte fått (?:några )?(?:specifika )?resultat)\b",
    flags=re.IGNORECASE,
)
_GENERATED_MEDIA = re.compile(
    r"!\[[^\]]*\]\([^)]*\)|data:image/",
    flags=re.IGNORECASE,
)
_UNSUPPORTED_CAUSATION = re.compile(
    r"\b(?:caused?|due to|driven by|influenced?|led to|resulted in|"
    r"seasonality|seasonal|på grund av|orsak(?:ad|ade|at)|drevs av|"
    r"drivet av|påverk(?:ade|at)|ledde till|säsong(?:smönster|sbetonad|seffekt)?)\b",
    flags=re.IGNORECASE,
)


def _generated_analysis_is_compatible(
    analysis: str,
    facts: dict[str, Any],
) -> bool:
    if not analysis.strip():
        return False
    if facts_have_data(facts) and _FALSE_NO_DATA.search(analysis):
        return False
    if _GENERATED_MEDIA.search(analysis):
        return False
    if _UNSUPPORTED_CAUSATION.search(analysis):
        return False
    comparison = facts.get("comparison_period")
    effective = facts.get("effective_period")
    if (
        isinstance(comparison, dict)
        and comparison.get("start")
        and comparison.get("end")
        and (
            "%" in analysis
            or re.search(r"\bprevious period\b|\bföregående period\b", analysis, re.IGNORECASE)
        )
        and (
            str(comparison["start"]) not in analysis
            or str(comparison["end"]) not in analysis
            or (
                isinstance(effective, dict)
                and effective.get("start")
                and effective.get("end")
                and (
                    str(effective["start"]) not in analysis
                    or str(effective["end"]) not in analysis
                )
            )
        )
    ):
        return False
    return True


def build_compose_response_node() -> BaseNode:
    def compose_response(
        ctx: Context,
        tool_results: list[dict[str, Any]] | None = None,
        visualization_plan: Any = None,
        visualization_datasets_json: Any = "[]",
        analysis: str | None = None,
        direct_message: str | None = None,
        canonical_request_json: Any = "null",
        effective_mode: str = "",
        conversation_id: str = "",
        ui_language: str = "en",
        analysis_facts_json: Any = "{}",
    ) -> None:
        results = [
            ExecutedToolCall.model_validate(
                result
            )
            for result in (tool_results or [])
        ]
        viz = _coerce_viz(
            visualization_plan
        )
        viz_datasets = _coerce_viz_datasets(
            visualization_datasets_json
        )

        valid_dataset_ids = {
            dataset.id
            for dataset in viz_datasets
        }
        specs = [
            spec
            for spec in viz.visualizations
            if spec.dataset in valid_dataset_ids
        ]

        request = coerce_request(
            canonical_request_json
        )
        facts = _coerce_facts(analysis_facts_json)

        generated_analysis = (analysis or "").strip()
        if generated_analysis and not _generated_analysis_is_compatible(
            generated_analysis,
            facts,
        ):
            generated_analysis = render_analysis_facts(facts, ui_language)

        message = (
            (direct_message or "").strip()
            or generated_analysis
        )

        if (
            not message
            and request is not None
        ):
            message = build_short_answer(
                request,
                results,
                ui_language,
                effective_mode=effective_mode,
            ).strip()

        if not message and specs:
            message = (
                "Här är resultatet."
                if ui_language == "sv"
                else "Here is the result."
            )

        if not message and not specs:
            message = (
                "Inget svar kunde genereras."
                if ui_language == "sv"
                else "No response was produced."
            )

        response = AgentQueryResponse(
            conversation_id=conversation_id,
            message=message,
            tool_calls=[
                ToolCallInfo(
                    call_id=result.call_id,
                    tool_name=result.tool_name,
                    arguments=result.arguments,
                    purpose=result.purpose,
                    status=result.status,
                    error=result.error,
                )
                for result in results
            ],
            datasets=[
                Dataset(
                    call_id=result.call_id,
                    tool_name=result.tool_name,
                    status=(
                        result.status
                        or "success"
                    ),
                    result=result.result or {},
                )
                for result in results
                if result.is_success
            ],
            visualization_datasets=viz_datasets,
            visualizations=specs,
        )

        ctx.state[
            StateKeys.RESPONSE
        ] = response.model_dump(
            mode="json"
        )

    return node(
        compose_response,
        name="compose_response",
    )
