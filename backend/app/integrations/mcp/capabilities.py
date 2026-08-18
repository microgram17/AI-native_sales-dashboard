"""Discover domain capabilities from MCP tool input schemas.

The agent application reasons in semantic capabilities (summary, ranking, trend,
product overview and product resolution), not concrete MCP tool names. Concrete
tool names are discovered from `list_tools()` on every request.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Protocol


CAP_PRODUCT_RESOLVER = "product_resolver"
CAP_SUMMARY = "summary"
CAP_RANKING = "ranking"
CAP_TREND = "trend"
CAP_PRODUCT_OVERVIEW = "product_overview"


class ToolDefinitionLike(Protocol):
    name: str
    input_schema: dict[str, Any]


class McpCapabilityError(RuntimeError):
    """Discovered MCP contracts cannot be mapped unambiguously to capabilities."""


def _properties(tool: ToolDefinitionLike) -> set[str]:
    schema = tool.input_schema or {}
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return set()
    return set(properties)


def _classify(tool: ToolDefinitionLike) -> str | None:
    props = _properties(tool)

    if {"group_by", "rank_by"}.issubset(props):
        return CAP_RANKING

    if "grain" in props and {"period_start", "period_end"}.issubset(props):
        return CAP_TREND

    if "product" in props:
        if "period_start" in props or "period_end" in props or "scope" in props:
            return CAP_PRODUCT_OVERVIEW
        return CAP_PRODUCT_RESOLVER

    if {"period_start", "period_end", "scope"}.issubset(props):
        return CAP_SUMMARY

    return None


def discover_capabilities(
    tools: list[ToolDefinitionLike],
) -> dict[str, str]:
    """Map semantic capability -> currently discovered concrete MCP tool name.

    Classification uses the public input contract rather than concrete names.
    Ambiguous duplicate capabilities are rejected rather than arbitrarily
    selecting one.
    """

    candidates: dict[str, list[str]] = defaultdict(list)

    for tool in tools:
        capability = _classify(tool)
        if capability is not None:
            candidates[capability].append(tool.name)

    ambiguous = {
        capability: names
        for capability, names in candidates.items()
        if len(names) > 1
    }
    if ambiguous:
        detail = "; ".join(
            f"{capability}: {', '.join(sorted(names))}"
            for capability, names in sorted(ambiguous.items())
        )
        raise McpCapabilityError(
            f"Ambiguous MCP analytics capabilities discovered: {detail}"
        )

    return {
        capability: names[0]
        for capability, names in candidates.items()
        if names
    }
