# Supplier Sales Analytics — Capabilities

This MCP server exposes four domain-oriented analytics tools over a single
supplier's completed sales. The supplier identity is always resolved server-side
from trusted context and is never a model-visible argument.

## Tools

| Tool | Purpose |
| --- | --- |
| `sales_summary` | Overall KPI summary for a period and optional scope, with period-over-period comparison. |
| `sales_rank` | Rank products / categories / stores / cities / channels by a chosen metric, with full context. |
| `sales_trend` | Ordered time series (day/week/month/quarter), optionally split into a few top series. |
| `product_overview` | Rich single-product deep dive assembled from several queries. |

All tools return typed structured output (semantic analytical data only — no
chart or visualization instructions).

## Supported questions

- Sales KPIs: units, gross sales, net sales, discounts, orders, average selling
  price, discount rate.
- Rankings and breakdowns across products, categories, stores, cities, channels.
- Time trends at day / week / month / quarter grain, optionally split by a
  dimension.
- Period-over-period change (when an explicit finite period is supplied; the
  immediately preceding period of equal length is used).
- Product overviews: summary, rank among supplier products, share of supplier
  units and net sales, monthly trend, channel and city breakdowns.
- Discount behavior via the `discounts` and `discount_rate` metrics.

## Scope filters

Every tool accepts an optional `scope` object: `channels`, `cities`,
`store_ids`, `categories`, `product_ids`. Empty lists mean no restriction.

## Period behavior

- Supply `period_start` and `period_end` together, or omit both.
- When omitted, the full available supplier date range is used and no
  period-over-period comparison is produced.
- The effective period (and comparison period, when present) is always returned.

## NOT supported (would require new data or approvals)

- Retailer or overall-market share (only this supplier's own sales are present).
- Competitor performance.
- Inventory, stock levels or availability.
- Returns / refunds.
- Customer demographics or segmentation.
- Causal explanations of *why* sales changed.
- Forecasts or predictions of future sales.
- Profit or margin (cost-based metrics are not exposed for supplier access).

## Interpretation guidance

The tools return data that can help an analytics agent form hypotheses (for
example, a discount-rate change alongside a units change). They do not establish
causation; correlations must not be presented as proven causes.

## Order-count semantics

Distinct order counts are computed at the grain of the selected analytical view
and are not additive across the entity axis. For `sales_rank` with
`rank_by="orders"`, `share_of_rank_metric` is share of *order participation*: an
order containing several ranked entities is counted once per entity, so those
shares describe participation rather than mutually exclusive order ownership.
