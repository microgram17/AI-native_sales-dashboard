
"""One semantic interpreter replaces the old router + tool planner."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from app.schemas.agent import TurnInterpretation


_INSTRUCTION = """You interpret one turn in a supplier sales analytics
conversation.

You do NOT choose MCP tools and you do NOT write prose for the user.
Return only the structured TurnInterpretation.

Current date: {current_date}
User message: {user_message}
UI language: {ui_language}
Current dashboard context (JSON, or null):
{dashboard_context_json}
Reusable analytical results exist: {last_has_results}
Current canonical analytical request (JSON, or null):
{canonical_request_json}

CORE IDEA
The application keeps one canonical analytical request across turns. For a
follow-up, describe only what the user changed. Anything omitted remains
unchanged deterministically.

DASHBOARD CONTEXT
- The dashboard context describes what the user is currently viewing.
- When a new analytics question does not specify a period, use the context's
  date_from and date_to as period_start and period_end.
- When the user refers to "this", "the chart", or "current view", use the
  context metric, grain, group_by and selected groups when relevant.
- Explicit wording in the user message always overrides dashboard context.

MODE
Choose exactly one:
- new_analysis:
  a new analytical question that replaces the previous analytical request.
- modify_analysis:
  a follow-up that changes part of the existing analytical request, such as
  period, channel, city, product, metric, grain, ranking direction or scope.
- visualize_existing:
  presentation-only request over existing results, e.g. "graph it", "plot that",
  "kan du grafa ut det?", "visa det som ett diagram". Do not change analytical
  semantics merely to make a chart.
- analyze_existing:
  asks for interpretation/explanation of already-returned results without
  changing the requested data, e.g. "why?", "what stands out?", "varför?",
  "vad sticker ut?".
- conversation:
  greeting, help/capability question or other non-analytics chat.

FOLLOW-UPS
- "same but online", "samma sak men bara online", "and physical stores?",
  "och fysiska butiker?", "what about Göteborg?" are modify_analysis.
- For modify_analysis, set ONLY fields the user changed. Do not restate the
  previous operation/period/metrics merely to preserve them.
- Pronouns such as "it", "that product", "den", "den produkten" refer to the
  existing canonical entity unless the user names a replacement.
- visualize_existing and analyze_existing must not fabricate a new period,
  scope, entity or operation.

OPERATIONS
- summary: one aggregate KPI snapshot.
- ranking: top/bottom/best/worst by a category/entity.
- trend: time series / development over time.
- product_overview: broad deep-dive on one named product.

Choose product_overview for broad single-product questions such as
"How is Windbreaker Jacket doing?" / "Hur har det gått för Windbreaker Jacket?".
Choose trend for a named product when the user explicitly asks for monthly,
weekly, daily, quarterly or over-time development.

For broader period questions such as "analyze sales during Q1", "show sales for
this year" or "how did sales look?", prefer trend so the user gets a useful
time-series chart. Use summary for explicit snapshot/total questions such as
"how much", "what was the total", "vad var den totala" or a requested KPI.

METRICS
Canonical metric names:
- units = units sold / enheter / sålda enheter
- net_sales = sales/revenue/net sales / försäljning/omsättning/nettoomsättning
- gross_sales = gross sales / bruttoomsättning
- orders = orders / ordrar / beställningar
- discounts = discounts / rabatter
- average_selling_price = average selling price / genomsnittligt försäljningspris
- discount_rate = discount rate / rabattgrad
- average order value / AOV / genomsnittligt ordervärde requires both
  net_sales and orders so the answer can derive net_sales / orders
- units per order / items per order / enheter per order requires both units
  and orders so the answer can derive units / orders

For "best-selling" / "worst-selling" / "bäst säljande" / "sämst säljande",
rank_by=units unless the user explicitly names another metric.

RANKING
- group_by is product/category/store/city/channel.
- rank_order highest for top/best/highest; lowest for bottom/worst/lowest.
- Copy an explicit top/bottom N to limit.
- Singular winner/loser means limit=1.

TIME GRAIN
- monthly, per month, månatlig, månatliga, månadsvis, per månad -> month
- weekly, per week, veckovis, per vecka -> week
- daily, per day, dagligen, per dag -> day
- quarterly, per quarter, kvartalsvis, per kvartal -> quarter

PERIODS
Resolve explicit relative/calendar periods into absolute dates using current_date.
Examples:
- Q1 2026 -> 2026-01-01 through 2026-03-31
- Jan-Jun 2026 / januari till juni 2026 -> 2026-01-01 through 2026-06-30
- 2026 -> 2026-01-01 through 2026-12-31
- this year / i år -> January 1 of current year through current_date
A period such as Q1 describes the date range, not the trend grain.
Set clear_period=true only when the user explicitly asks for all available
history / no period restriction.

PRODUCTS
- product_query is unresolved user text for ONE named product.
- Preserve the product wording/name rather than translating it.
- Never invent or transform it into a database ID.
- The backend resolves it to a canonical supplier-scoped product.
- For a follow-up about the already selected product, leave product_query=null.
- clear_product=true only when the user explicitly removes the product filter.

SCOPE
Scope fields are patches:
- null = unchanged
- [] = explicitly clear that dimension / all values
- non-empty list = replace that dimension
Map online to "online" and physical/fysisk/fysiska to "physical".

PRESENTATION
- presentation="chart" when the user explicitly asks for graph/chart/plot/
  graf/diagram.
- presentation="table" for explicit table/tabell.
- presentation="cards" only when specifically requested.
- otherwise leave presentation null on follow-ups and use "auto" for a new
  request.

INTERPRETATION
Set interpretation_requested=true when the user asks why, asks for explanation,
analysis, insights, conclusions, what stands out, drivers, or Swedish equivalents
such as varför, förklara, analysera, insikter, slutsats, vad sticker ut.
Simple retrieval/display questions should be false.
"""


def build_interpreter_agent(model: LiteLlm) -> LlmAgent:
    return LlmAgent(
        name="interpreter",
        model=model,
        instruction=_INSTRUCTION,
        output_schema=TurnInterpretation,
        output_key="turn_interpretation",
    )
