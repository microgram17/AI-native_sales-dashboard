
"""Pure semantic request-state logic.

The LLM supplies a semantic patch. This module owns deterministic continuity,
high-confidence wording fallbacks and canonical request defaults.
"""

from __future__ import annotations

import calendar
import json
import re
from copy import deepcopy
from datetime import date
from typing import Any

from app.schemas.agent import (
    AnalysisRequestState,
    AnalysisScope,
    DashboardContext,
    Metric,
    ScopePatch,
    TurnInterpretation,
    TurnMode,
)


_DASHBOARD_REFERENCE_PATTERNS = (
    r"\bcurrent\s+(?:dashboard\s+)?view\b",
    r"\bthis\s+(?:dashboard|view|chart|graph)\b",
    r"\bthe\s+(?:current\s+)?(?:chart|graph)\b",
    r"\baktuella\s+dashboardvyn\b",
    r"\bden\s+(?:här|aktuella)\s+(?:dashboardvyn|vyn|grafen|diagrammet)\b",
    r"\b(?:grafen|diagrammet)\b",
)


_INTERPRETATION_PATTERNS = (
    r"\bwhy\b",
    r"\bexplain\b",
    r"\bwhat\s+(?:stands?|stood)\s+out\b",
    r"\binsight(?:s)?\b",
    r"\banaly[sz]e\b",
    r"\bconclusion(?:s)?\b",
    r"\bwhat\s+drove\b",
    r"\bvarför\b",
    r"\bförklara\b",
    r"\bvad\s+sticker\s+ut\b",
    r"\binsikt(?:er)?\b",
    r"\banalysera\b",
    r"\bslutsats(?:er)?\b",
    r"\bvad\s+drev\b",
)

_GRAPH_PATTERNS = (
    r"\bgraph\b",
    r"\bchart\b",
    r"\bplot\b",
    r"\bline\s+(?:chart|graph|plot)\b",
    r"\blinjegraf(?:en|er)?\b",
    r"\blinjediagram(?:met|men)?\b",
    r"\bgraf(?:a|en|er|iskt)?\b",
    r"\bdiagram\b",
)

_LINE_CHART_PATTERNS = (
    r"\bline\s+(?:chart|graph|plot)\b",
    r"\blinjegraf(?:en|er)?\b",
    r"\blinjediagram(?:met|men)?\b",
)

_TABLE_PATTERNS = (
    r"\btable\b",
    r"\btabell\b",
)

_MONTH_GRAIN = (
    r"\bmonthly\b",
    r"\bper\s+month\b",
    r"\bmånatlig(?:a|t)?\b",
    r"\bmånadsvis\b",
    r"\bper\s+månad\b",
)
_WEEK_GRAIN = (
    r"\bweekly\b",
    r"\bper\s+week\b",
    r"\bveckovis\b",
    r"\bper\s+vecka\b",
)
_DAY_GRAIN = (
    r"\bdaily\b",
    r"\bper\s+day\b",
    r"\bdagligen\b",
    r"\bper\s+dag\b",
)
_QUARTER_GRAIN = (
    r"\bquarterly\b",
    r"\bper\s+quarter\b",
    r"\bkvartalsvis\b",
    r"\bper\s+kvartal\b",
)


_TREND_PATTERNS = (
    r"\btrend\b",
    r"\bover\s+time\b",
    r"\bdevelopment\s+over\s+time\b",
    r"\bdevelop(?:ed|ment|ing)?\s+over\s+time\b",
    r"\bmonth\s+by\s+month\b",
    r"\bweek\s+by\s+week\b",
    r"\bquarter\s+by\s+quarter\b",
    r"\butveckling\s+över\s+tid\b",
    r"\böver\s+tid\b",
    r"\butveckl(?:ats|as|ing)\b",
)

_PRODUCT_OVERVIEW_PATTERNS = (
    r"\bhow\s+is\b",
    r"\bhow\s+has\b",
    r"\bperformance\b",
    r"\bproduct\s+overview\b",
    r"\boverview\b",
    r"\bhur\s+går\b",
    r"\bhur\s+har\b",
    r"\bprester(?:ar|at|ade|ation)?\b",
    r"\bproduktöversikt\b",
    r"\böversikt\b",
)

_SUMMARY_PATTERNS = (
    r"\bsummary\b",
    r"\bsummar(?:ize|ise)\b",
    r"\boverall\b",
    r"\btotals?\b",
    r"\bsammanfatt(?:a|ning)\b",
    r"\böversikt\b",
    r"\btotal(?:t|er)?\b",
)

_BROAD_ANALYSIS_PATTERNS = (
    r"\banaly[sz](?:e|ing|is)?\b",
    r"\bwhat\s+stands?\s+out\b",
    r"\bshow(?:\s+me)?\b",
    r"\bhow\s+(?:did|has|have|is|are|was|were)\b",
    r"\boverview\b",
    r"\banalysera\b",
    r"\bvad\s+sticker\s+ut\b",
    r"\bvisa\b",
    r"\bhur\s+(?:gick|går|har|såg|ser|var)\b",
    r"\böversikt\b",
)

_SNAPSHOT_PATTERNS = (
    r"\bhow\s+much\b",
    r"\bwhat\s+(?:is|was|were)\s+(?:the\s+)?(?:total\s+)?",
    r"\btotal(?:s|led)?\b",
    r"\bsum(?:mary)?\b",
    r"\bkpi\b",
    r"\bhur\s+mycket\b",
    r"\bvad\s+(?:är|var|blev)\s+(?:den\s+)?(?:totala\s+)?",
    r"\btotal(?:t|en|a)?\b",
    r"\bsumma\b",
    r"\bsammanfatt(?:a|ning)\b",
)

_RANKING_PATTERNS = (
    r"\btop\b",
    r"\bbottom\b",
    r"\bbest\b",
    r"\bworst\b",
    r"\bhighest\b",
    r"\blowest\b",
    r"\brank(?:ing|ed)?\b",
    r"\btopp\b",
    r"\bbotten\b",
    r"\bbäst\b",
    r"\bsämst\b",
    r"\bhögst\b",
    r"\blägst\b",
    r"\brangordn(?:a|ing)\b",
)

_MODIFIER_PATTERNS = (
    r"^and\b",
    r"^och\b",
    r"^what about\b",
    r"^vad sägs om\b",
    r"\bsame thing\b",
    r"\bsame but\b",
    r"\bsamma sak\b",
    r"\bsamma men\b",
)


_RANK_MORE_PATTERNS = (
    r"^show\s+more\b",
    r"^show\s+me\s+more\b",
    r"^can\s+you\s+show\s+(?:me\s+)?more\b",
    r"^more\s+(?:results?|products?|items?)\b",
    r"^visa\s+fler\b",
    r"^kan\s+du\s+visa\s+fler\b",
    r"^fler\s+(?:resultat|produkter|poster)\b",
)

_RANK_FEWER_PATTERNS = (
    r"^show\s+fewer\b",
    r"^show\s+me\s+fewer\b",
    r"^can\s+you\s+show\s+(?:me\s+)?fewer\b",
    r"^fewer\s+(?:results?|products?|items?)\b",
    r"^visa\s+färre\b",
    r"^kan\s+du\s+visa\s+färre\b",
    r"^färre\s+(?:resultat|produkter|poster)\b",
)

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "en": 1,
    "ett": 1,
    "två": 2,
    "tre": 3,
    "fyra": 4,
    "fem": 5,
    "sex": 6,
    "sju": 7,
    "åtta": 8,
    "nio": 9,
    "tio": 10,
}

_MONTHS = {
    "january": 1, "jan": 1, "januari": 1,
    "february": 2, "feb": 2, "februari": 2,
    "march": 3, "mar": 3, "mars": 3,
    "april": 4, "apr": 4,
    "may": 5, "maj": 5,
    "june": 6, "jun": 6, "juni": 6,
    "july": 7, "jul": 7, "juli": 7,
    "august": 8, "aug": 8, "augusti": 8,
    "september": 9, "sep": 9,
    "october": 10, "oct": 10, "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def coerce_interpretation(value: Any) -> TurnInterpretation:
    if isinstance(value, TurnInterpretation):
        return value
    if isinstance(value, dict):
        return TurnInterpretation.model_validate(value)
    if isinstance(value, str) and value.strip():
        return TurnInterpretation.model_validate_json(value)
    return TurnInterpretation(mode="conversation")


def coerce_request(value: Any) -> AnalysisRequestState | None:
    if value is None:
        return None
    if isinstance(value, AnalysisRequestState):
        return value
    if isinstance(value, dict):
        try:
            return AnalysisRequestState.model_validate(value)
        except Exception:
            return None
    if isinstance(value, str) and value.strip() and value.strip() != "null":
        try:
            return AnalysisRequestState.model_validate_json(value)
        except Exception:
            return None
    return None


def coerce_dashboard_context(value: Any) -> DashboardContext | None:
    if value is None:
        return None
    if isinstance(value, DashboardContext):
        return value
    if isinstance(value, dict):
        try:
            return DashboardContext.model_validate(value)
        except Exception:
            return None
    if isinstance(value, str) and value.strip() and value.strip() != "null":
        try:
            return DashboardContext.model_validate_json(value)
        except Exception:
            return None
    return None


def request_to_json(request: AnalysisRequestState | None) -> str:
    if request is None:
        return "null"
    return request.model_dump_json()


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def references_dashboard_context(text: str) -> bool:
    return _matches_any(text.casefold(), _DASHBOARD_REFERENCE_PATTERNS)


def _infer_grain(text: str) -> str | None:
    if _matches_any(text, _MONTH_GRAIN):
        return "month"
    if _matches_any(text, _WEEK_GRAIN):
        return "week"
    if _matches_any(text, _DAY_GRAIN):
        return "day"
    if _matches_any(text, _QUARTER_GRAIN):
        return "quarter"
    return None


def _infer_presentation(text: str) -> str | None:
    if _matches_any(text, _GRAPH_PATTERNS):
        return "chart"
    if _matches_any(text, _TABLE_PATTERNS):
        return "table"
    return None


def _infer_interpretation(text: str) -> bool:
    return _matches_any(text, _INTERPRETATION_PATTERNS)


def _infer_channels(text: str) -> list[str] | None:
    lowered = text.casefold()

    if re.search(r"\b(?:all channels|alla kanaler|båda kanaler)\b", lowered):
        return []
    if re.search(r"\b(?:online|webb|webshop)\b", lowered):
        return ["online"]
    if re.search(
        r"\b(?:physical(?: stores?)?|fysisk(?:a)?(?: butiker?)?)\b",
        lowered,
    ):
        return ["physical"]

    return None


def _infer_metrics(text: str) -> list[Metric]:
    lowered = text.casefold()
    metrics: list[Metric] = []

    if re.search(
        r"\b(?:average order value|aov|genomsnittligt ordervärde)\b",
        lowered,
    ):
        metrics.extend(["net_sales", "orders"])

    if re.search(
        r"\b(?:units per order|items per order|enheter per order)\b",
        lowered,
    ):
        metrics.extend(["units", "orders"])

    patterns: tuple[tuple[Metric, tuple[str, ...]], ...] = (
        ("units", (
            r"\bunits?\b",
            r"\bunits sold\b",
            r"\benheter\b",
            r"\bsålda enheter\b",
        )),
        ("net_sales", (
            r"\bnet sales\b",
            r"\bnet revenue\b",
            r"\bnettoomsättning\b",
            r"\bnettoförsäljning\b",
        )),
        ("gross_sales", (
            r"\bgross sales\b",
            r"\bbruttoomsättning\b",
        )),
        ("orders", (
            r"\borders?\b",
            r"\bordrar\b",
            r"\bbeställningar\b",
        )),
        ("discounts", (
            r"\bdiscounts?\b",
            r"\brabatter\b",
        )),
        ("average_selling_price", (
            r"\baverage selling price\b",
            r"\bavg selling price\b",
            r"\bgenomsnittligt försäljningspris\b",
        )),
        ("discount_rate", (
            r"\bdiscount rate\b",
            r"\brabattgrad\b",
        )),
    )

    for metric, expressions in patterns:
        if any(re.search(expr, lowered) for expr in expressions):
            if metric not in metrics:
                metrics.append(metric)

    if (
        "net_sales" not in metrics
        and "gross_sales" not in metrics
        and re.search(
            r"\b(?:revenue|sales|försäljning|omsättning|intäkter)\b",
            lowered,
        )
    ):
        metrics.append("net_sales")

    return metrics


def _infer_rank_limit(text: str) -> int | None:
    """Infer an explicit/default ranking size from the raw wording.

    Singular winner questions default to one result. Plural ranking questions
    default to five results. This distinction is important for wording such as
    "Vilka produkter säljer bäst?" where "bäst" describes a ranking, not a
    request for exactly one winner.
    """

    lowered = text.casefold()

    match = re.search(
        r"\b(?:top|bottom|topp|botten)\s+"
        r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"en|ett|två|tre|fyra|fem|sex|sju|åtta|nio|tio)\b",
        lowered,
    )
    if match:
        token = match.group(1)
        value = int(token) if token.isdigit() else _NUMBER_WORDS.get(token)
        if value is not None:
            return max(1, min(value, 20))

    ranking_word = re.search(
        r"\b(?:best|worst|highest|lowest|bäst|sämst|högst|lägst)\b",
        lowered,
    )
    if not ranking_word:
        return None

    plural_group = re.search(
        r"\b(?:"
        r"which\s+(?:products?|categories|stores|cities|channels)|"
        r"what\s+(?:products?|categories|stores|cities|channels)|"
        r"products?|categories|stores|cities|channels|"
        r"vilka\s+(?:produkter|kategorier|butiker|städer|kanaler)|"
        r"produkter|kategorier|butiker|städer|kanaler"
        r")\b",
        lowered,
    )
    if plural_group:
        return 5

    return 1


def _rank_limit_followup_direction(text: str) -> str | None:
    lowered = text.casefold().strip()
    if _matches_any(lowered, _RANK_MORE_PATTERNS):
        return "more"
    if _matches_any(lowered, _RANK_FEWER_PATTERNS):
        return "fewer"
    return None


def _rank_followup_limit(
    current_limit: int,
    text: str,
) -> int | None:
    direction = _rank_limit_followup_direction(text)
    if direction is None:
        return None

    current = max(1, min(int(current_limit), 20))

    if direction == "more":
        if current < 5:
            return 5
        return min(20, current + 5)

    if current <= 5:
        return 1
    return max(5, current - 5)


def _infer_rank_order(text: str) -> str | None:
    lowered = text.casefold()
    if re.search(r"\b(?:worst|lowest|bottom|sämst|lägst|botten)\b", lowered):
        return "lowest"
    if re.search(r"\b(?:best|highest|top|bäst|högst|topp)\b", lowered):
        return "highest"
    return None


def _infer_group_by(text: str) -> str | None:
    lowered = text.casefold()
    if re.search(r"\b(?:products?|produkter?)\b", lowered):
        return "product"
    if re.search(r"\b(?:categories|category|kategorier|kategori)\b", lowered):
        return "category"
    if re.search(r"\b(?:cities|city|städer|stad)\b", lowered):
        return "city"
    if re.search(r"\b(?:channels|channel|kanaler|kanal)\b", lowered):
        return "channel"
    if re.search(r"\b(?:stores|store|butiker|butik)\b", lowered):
        return "store"
    return None


def _infer_rank_by(text: str) -> str | None:
    metrics = _infer_metrics(text)
    for metric in metrics:
        if metric in {
            "units",
            "net_sales",
            "gross_sales",
            "discounts",
            "orders",
        }:
            return metric

    lowered = text.casefold()
    if re.search(r"\b(?:best-selling|worst-selling|bäst säljande|sämst säljande)\b", lowered):
        return "units"
    return None


def _has_explicit_line_chart_intent(text: str) -> bool:
    return _matches_any(
        text.casefold(),
        _LINE_CHART_PATTERNS,
    )


def _has_explicit_trend_intent(text: str) -> bool:
    lowered = text.casefold()
    return (
        _infer_grain(lowered) is not None
        or _matches_any(lowered, _TREND_PATTERNS)
        or _has_explicit_line_chart_intent(lowered)
    )


def _has_broad_analysis_intent(text: str) -> bool:
    lowered = text.casefold()
    return (
        _matches_any(lowered, _BROAD_ANALYSIS_PATTERNS)
        and not _matches_any(lowered, _SNAPSHOT_PATTERNS)
    )


def _infer_explicit_operation(
    text: str,
    product_query: str | None = None,
) -> str | None:
    """Return only high-confidence operation cues from the raw user wording.

    Period labels such as Q1/Q2 are intentionally not trend/grain cues. This
    lets deterministic semantics overrule an LLM that turns "during Q1" into
    grain="quarter".
    """
    lowered = text.casefold()

    if _has_explicit_trend_intent(lowered):
        return "trend"

    if _matches_any(lowered, _RANKING_PATTERNS):
        return "ranking"

    if (
        product_query
        and _matches_any(lowered, _PRODUCT_OVERVIEW_PATTERNS)
    ):
        return "product_overview"

    if (
        _matches_any(lowered, _SUMMARY_PATTERNS)
        and not _has_broad_analysis_intent(lowered)
    ):
        return "summary"

    return None


def _infer_operation(
    text: str,
    product_query: str | None = None,
) -> str:
    return (
        _infer_explicit_operation(text, product_query)
        or "summary"
    )

def _month_range_from_text(text: str) -> tuple[date, date] | None:
    lowered = text.casefold()
    names = sorted(_MONTHS, key=len, reverse=True)
    name_pattern = "|".join(re.escape(name) for name in names)

    match = re.search(
        rf"\b({name_pattern})\b"
        rf"\s*(?:-|–|to|through|till|till och med)\s*"
        rf"\b({name_pattern})\b"
        rf".*?\b(20\d{{2}})\b",
        lowered,
    )
    if not match:
        return None

    first = _MONTHS[match.group(1)]
    second = _MONTHS[match.group(2)]
    year = int(match.group(3))
    if first > second:
        return None

    return (
        date(year, first, 1),
        date(year, second, calendar.monthrange(year, second)[1]),
    )


def _infer_period(text: str, current_date: date) -> tuple[date, date] | None:
    lowered = text.casefold()

    month_range = _month_range_from_text(lowered)
    if month_range:
        return month_range

    year_match = re.search(r"\b(20\d{2})\b", lowered)
    year = int(year_match.group(1)) if year_match else current_date.year

    quarter = re.search(r"\bq([1-4])\b", lowered)
    if quarter:
        q = int(quarter.group(1))
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        return (
            date(year, start_month, 1),
            date(year, end_month, calendar.monthrange(year, end_month)[1]),
        )

    if re.search(
        r"\b(?:first half|h1|first (?:2|two) quarters|"
        r"första halvåret|första (?:2|två) kvartalen)\b",
        lowered,
    ):
        return date(year, 1, 1), date(year, 6, 30)

    if re.search(r"\b(?:second half|h2|andra halvåret)\b", lowered):
        return date(year, 7, 1), date(year, 12, 31)

    if re.search(r"\b(?:this year|i år)\b", lowered):
        return date(current_date.year, 1, 1), current_date

    if year_match:
        return date(year, 1, 1), date(year, 12, 31)

    return None


def _is_presentation_only(
    text: str,
    *,
    inferred_grain: str | None,
    inferred_channels: list[str] | None,
    inferred_period: tuple[date, date] | None,
    inferred_metrics: list[Metric],
) -> bool:
    if _infer_presentation(text) is None:
        return False

    return not any(
        (
            inferred_grain is not None,
            inferred_channels is not None,
            inferred_period is not None,
            bool(inferred_metrics),
            _infer_group_by(text) is not None,
            _infer_rank_limit(text) is not None,
        )
    )


def effective_mode(
    interpretation: TurnInterpretation,
    *,
    previous: AnalysisRequestState | None,
    has_prior_results: bool,
    user_message: str,
    current_date: date,
) -> TurnMode:
    if previous is None:
        return interpretation.mode

    lowered = user_message.casefold().strip()
    grain = _infer_grain(lowered)
    channels = _infer_channels(lowered)
    period = _infer_period(lowered, current_date)
    metrics = _infer_metrics(lowered)

    if (
        previous.operation == "ranking"
        and _rank_limit_followup_direction(lowered) is not None
    ):
        return "modify_analysis"

    if (
        has_prior_results
        and _has_explicit_line_chart_intent(lowered)
    ):
        # A line chart needs an X-axis progression. Reuse an existing trend
        # (or the rich monthly trend inside product_overview), but a summary
        # snapshot/comparison must be re-queried as a trend.
        if previous.operation in {
            "trend",
            "product_overview",
        }:
            return "visualize_existing"
        if previous.operation == "summary":
            return "modify_analysis"

    if has_prior_results and _is_presentation_only(
        lowered,
        inferred_grain=grain,
        inferred_channels=channels,
        inferred_period=period,
        inferred_metrics=metrics,
    ):
        return "visualize_existing"

    if has_prior_results and _infer_interpretation(lowered):
        if not any((grain, channels is not None, period, metrics)):
            return "analyze_existing"

    if (
        interpretation.mode == "new_analysis"
        and _matches_any(lowered, _MODIFIER_PATTERNS)
    ):
        return "modify_analysis"

    return interpretation.mode


def _apply_scope_patch(
    base: AnalysisScope,
    patch: ScopePatch,
    text: str,
) -> AnalysisScope:
    values = base.model_dump()

    for key in ("channels", "cities", "store_ids", "categories"):
        value = getattr(patch, key)
        if value is not None:
            values[key] = deepcopy(value)

    if patch.channels is None:
        inferred = _infer_channels(text)
        if inferred is not None:
            values["channels"] = inferred

    return AnalysisScope.model_validate(values)


def _default_metrics(
    operation: str,
    rank_by: str | None = None,
) -> list[Metric]:
    if operation == "ranking":
        return [rank_by or "units"]  # type: ignore[list-item]
    if operation == "trend":
        return ["net_sales"]
    return [
        "units",
        "net_sales",
        "orders",
        "average_selling_price",
    ]


def _normalize_operation_fields(
    request: AnalysisRequestState,
) -> AnalysisRequestState:
    updates: dict[str, Any] = {}

    if request.operation == "trend":
        updates["grain"] = request.grain or "month"
        updates["group_by"] = None
        updates["rank_by"] = None
        if not request.metrics:
            updates["metrics"] = ["net_sales"]

    elif request.operation == "ranking":
        rank_by = request.rank_by or "units"
        updates.update(
            {
                "grain": None,
                "split_by": None,
                "group_by": request.group_by or "product",
                "rank_by": rank_by,
                "metrics": request.metrics or [rank_by],
            }
        )

    elif request.operation == "product_overview":
        updates.update(
            {
                "grain": None,
                "group_by": None,
                "rank_by": None,
                "split_by": None,
            }
        )
        if not request.metrics:
            updates["metrics"] = _default_metrics("product_overview")

    else:
        updates.update(
            {
                "grain": None,
                "group_by": None,
                "rank_by": None,
                "split_by": None,
            }
        )
        if not request.metrics:
            updates["metrics"] = _default_metrics("summary")

    return request.model_copy(update=updates)


def apply_dashboard_context(
    request: AnalysisRequestState,
    dashboard: DashboardContext | None,
    *,
    user_message: str,
) -> AnalysisRequestState:
    """Apply visible dashboard semantics without relying on the interpreter.

    Explicit wording remains authoritative. Selected series are inherited only
    when the user refers to the current view and its grouping matches the
    requested grouping, so a request for cities cannot accidentally retain
    store IDs from a store chart.
    """

    text = user_message.casefold()
    explicit_group = _infer_group_by(text)
    references_dashboard = references_dashboard_context(text)

    if dashboard is None and explicit_group is None:
        return request

    values = request.model_dump()
    explicit_operation = _infer_explicit_operation(
        text,
        request.pending_product_query,
    )

    if references_dashboard and dashboard is not None:
        if _infer_period(text, dashboard.date_to) is None:
            values["period_start"] = dashboard.date_from
            values["period_end"] = dashboard.date_to

        if not _infer_metrics(text) and dashboard.metric is not None:
            values["metrics"] = [dashboard.metric]

        if explicit_operation is None and dashboard.view is not None:
            values["operation"] = dashboard.view

    operation = values.get("operation")
    group = explicit_group or (
        dashboard.group_by
        if references_dashboard and dashboard is not None
        else None
    )

    if explicit_group is not None and operation == "summary":
        # "Sales by city/store/channel" is a grouped snapshot unless the user
        # or current dashboard explicitly asks for a time trend.
        operation = (
            dashboard.view
            if references_dashboard
            and dashboard is not None
            and dashboard.view is not None
            else "ranking"
        )
        values["operation"] = operation

    if operation == "trend":
        if group is not None:
            values["split_by"] = group
        if (
            references_dashboard
            and dashboard is not None
            and dashboard.grain is not None
            and _infer_grain(text) is None
        ):
            values["grain"] = dashboard.grain

        if (
            references_dashboard
            and dashboard is not None
            and group is not None
            and group == dashboard.group_by
            and dashboard.selected_group_ids
        ):
            selected = dashboard.selected_group_ids[:10]
            scope = AnalysisScope.model_validate(values.get("scope") or {})
            scope_values = scope.model_dump()
            if group == "store":
                scope_values["store_ids"] = selected
            elif group == "city":
                scope_values["cities"] = selected
            elif group == "channel":
                scope_values["channels"] = [
                    item.casefold()
                    for item in selected
                    if item.casefold() in {"online", "physical"}
                ]
            values["scope"] = scope_values
            values["series_limit"] = len(selected)

    elif operation == "ranking" and group is not None:
        values["group_by"] = group
        rank_metric = next(
            (
                metric
                for metric in values.get("metrics") or []
                if metric in {
                    "units",
                    "net_sales",
                    "gross_sales",
                    "discounts",
                    "orders",
                }
            ),
            None,
        )
        values["rank_by"] = rank_metric or values.get("rank_by") or "units"

    contextualized = AnalysisRequestState.model_validate(values)
    return _normalize_operation_fields(contextualized)


def build_new_request(
    interpretation: TurnInterpretation,
    *,
    user_message: str,
    current_date: date,
) -> AnalysisRequestState:
    text = user_message.casefold()

    inferred_grain = _infer_grain(text)
    inferred_metrics = _infer_metrics(text)
    inferred_period = _infer_period(text, current_date)
    explicit_operation = _infer_explicit_operation(
        text,
        interpretation.product_query,
    )

    # High-confidence wording wins over model output. Most importantly:
    # "Q1" is a period, not grain="quarter", and a broad named-product
    # performance question is product_overview unless the user explicitly asks
    # for a time-series/trend.
    operation = (
        explicit_operation
        or ("trend" if _has_broad_analysis_intent(text) else None)
        or interpretation.operation
        or _infer_operation(text, interpretation.product_query)
    )

    rank_by = (
        _infer_rank_by(text)
        or interpretation.rank_by
        if operation == "ranking"
        else None
    )
    group_by = (
        _infer_group_by(text)
        or interpretation.group_by
        if operation == "ranking"
        else None
    )
    limit = (
        _infer_rank_limit(text)
        or interpretation.limit
        if operation == "ranking"
        else None
    )
    rank_order = (
        _infer_rank_order(text)
        or interpretation.rank_order
        if operation == "ranking"
        else None
    )

    if interpretation.clear_period:
        period_start = None
        period_end = None
    elif inferred_period is not None:
        # Calendar expressions such as Q1 2026 are deterministic and should
        # not be weakened by an LLM-generated alternative.
        period_start, period_end = inferred_period
    else:
        period_start = interpretation.period_start
        period_end = interpretation.period_end

    if (
        operation == "trend"
        and period_start is None
        and period_end is None
    ):
        period_start = date(current_date.year, 1, 1)
        period_end = current_date

    if (
        operation == "product_overview"
        and explicit_operation == "product_overview"
        and not inferred_metrics
    ):
        # A broad product-performance question should stay broad even if the
        # model attached one arbitrary metric while misclassifying the request.
        metrics = _default_metrics("product_overview")
    else:
        metrics = (
            inferred_metrics
            or interpretation.metrics
            or _default_metrics(operation, rank_by)
        )

    presentation = (
        _infer_presentation(text)
        or interpretation.presentation
        or "auto"
    )

    scope = _apply_scope_patch(
        AnalysisScope(),
        interpretation.scope,
        text,
    )

    # Grain is accepted only when it is actually expressed in the raw user
    # message. If the user asks for a trend without a grain, normalization
    # deterministically defaults to month. This prevents Q1/Q2 from becoming
    # one-point quarterly trends because the model happened to emit "quarter".
    trusted_grain = (
        inferred_grain
        if operation == "trend"
        else None
    )

    request = AnalysisRequestState(
        operation=operation,
        metrics=metrics,
        grain=trusted_grain,
        group_by=group_by,
        rank_by=rank_by,
        rank_order=rank_order or "highest",
        limit=limit or (
            1
            if (
                operation == "ranking"
                and _infer_rank_limit(text) == 1
            )
            else 10
        ),
        split_by=interpretation.split_by,
        series_limit=interpretation.series_limit or 5,
        period_start=period_start,
        period_end=period_end,
        scope=scope,
        entity=None,
        pending_product_query=(
            interpretation.product_query.strip()
            if interpretation.product_query
            else None
        ),
        presentation=presentation,
        interpretation_requested=(
            interpretation.interpretation_requested
            or _infer_interpretation(text)
        ),
    )

    return _normalize_operation_fields(request)

def merge_request(
    previous: AnalysisRequestState,
    interpretation: TurnInterpretation,
    *,
    user_message: str,
    current_date: date,
) -> AnalysisRequestState:
    text = user_message.casefold()
    values = previous.model_dump()

    inferred_grain = _infer_grain(text)
    inferred_metrics = _infer_metrics(text)
    inferred_period = _infer_period(text, current_date)
    explicit_operation = _infer_explicit_operation(
        text,
        interpretation.product_query,
    )

    original_operation = previous.operation
    explicit_line_chart = (
        _has_explicit_line_chart_intent(text)
    )

    # A modify turn is a patch, not a replacement plan. The operation changes
    # only when the raw wording contains a high-confidence operation cue.
    # Therefore a model cannot turn "same thing but online" into a summary or
    # turn "what about Q1?" into a quarterly trend.
    if explicit_operation is not None:
        values["operation"] = explicit_operation

    if (
        explicit_line_chart
        and original_operation == "summary"
    ):
        values["operation"] = "trend"
        values["grain"] = None

        # Summary requests often carry the full default KPI set. A line chart
        # over all of them is noisy and does not match the comparison chart the
        # user just saw. Preserve a genuinely single-metric summary; otherwise
        # use net sales as the deterministic default.
        if not inferred_metrics:
            values["metrics"] = (
                list(previous.metrics)
                if len(previous.metrics) == 1
                else ["net_sales"]
            )

    if inferred_metrics:
        values["metrics"] = inferred_metrics
    elif interpretation.metrics is not None:
        values["metrics"] = list(interpretation.metrics)

    if inferred_grain is not None:
        values["grain"] = inferred_grain
        values["operation"] = "trend"
    elif explicit_operation == "trend":
        # Preserve a prior trend grain when there is one. A transition from a
        # non-trend operation gets the deterministic month default later.
        if original_operation != "trend":
            values["grain"] = None

    if values["operation"] == "ranking":
        values["group_by"] = (
            _infer_group_by(text)
            or interpretation.group_by
            or values.get("group_by")
            or "product"
        )
        values["rank_by"] = (
            _infer_rank_by(text)
            or interpretation.rank_by
            or values.get("rank_by")
            or "units"
        )
        values["rank_order"] = (
            _infer_rank_order(text)
            or interpretation.rank_order
            or values.get("rank_order")
            or "highest"
        )
        values["limit"] = (
            _infer_rank_limit(text)
            or _rank_followup_limit(
                int(values.get("limit") or 10),
                text,
            )
            or interpretation.limit
            or values.get("limit")
            or 10
        )

    if interpretation.split_by is not None:
        values["split_by"] = interpretation.split_by
    if interpretation.series_limit is not None:
        values["series_limit"] = interpretation.series_limit

    if interpretation.clear_period:
        values["period_start"] = None
        values["period_end"] = None
    elif inferred_period is not None:
        values["period_start"], values["period_end"] = inferred_period
    elif (
        interpretation.period_start is not None
        or interpretation.period_end is not None
    ):
        values["period_start"] = interpretation.period_start
        values["period_end"] = interpretation.period_end

    scope = _apply_scope_patch(
        AnalysisScope.model_validate(
            values.get("scope") or {}
        ),
        interpretation.scope,
        text,
    )
    values["scope"] = scope.model_dump()

    if interpretation.clear_product:
        values["entity"] = None
        values["pending_product_query"] = None
    elif interpretation.product_query:
        values["entity"] = None
        values["pending_product_query"] = (
            interpretation.product_query.strip()
        )

    presentation = (
        _infer_presentation(text)
        or interpretation.presentation
    )
    if presentation is not None:
        values["presentation"] = presentation

    values["interpretation_requested"] = (
        interpretation.interpretation_requested
        or _infer_interpretation(text)
    )

    operation_changed = (
        values["operation"] != original_operation
    )

    request = AnalysisRequestState.model_validate(values)

    if (
        request.operation == "trend"
        and request.period_start is None
        and request.period_end is None
    ):
        request = request.model_copy(
            update={
                "period_start": date(
                    current_date.year,
                    1,
                    1,
                ),
                "period_end": current_date,
            }
        )

    if operation_changed or inferred_grain is not None:
        request = _normalize_operation_fields(request)

    return request

def validate_request(request: AnalysisRequestState) -> str | None:
    if (request.period_start is None) != (request.period_end is None):
        return "period_start and period_end must be supplied together"

    if (
        request.period_start is not None
        and request.period_end is not None
        and request.period_start > request.period_end
    ):
        return "period_start must be on or before period_end"

    if request.operation == "trend" and (
        request.period_start is None or request.period_end is None
    ):
        return "trend requires a concrete period"

    if request.operation == "product_overview" and (
        request.entity is None and not request.pending_product_query
    ):
        return "product_overview requires a product"

    return None
