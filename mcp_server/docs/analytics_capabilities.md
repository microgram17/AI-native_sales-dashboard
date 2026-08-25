# Supplier Sales Analytics Capabilities

The MCP server exposes four domain analytics tools over the authenticated
supplier's completed sales. Supplier identity is resolved from trusted MCP
context and is never a model-visible argument.

## Tools

| Tool | Purpose |
| --- | --- |
| `sales_summary` | KPI summary for a period and optional scope, with period comparison. |
| `sales_rank` | Rank products, categories, stores, cities, or channels. |
| `sales_trend` | Ordered day/week/month/quarter time series, optionally split into series. |
| `product_overview` | Single-product metrics, ranks, trend, and breakdowns. |

`resolve_product` is a supporting entity-resolution tool used when another
analytics tool requires a canonical product ID.

## Structured output

Every analytics tool returns the same typed `AnalyticsResult`:

- `status`: `success`, `no_data`, `not_found`, or `ambiguous`.
- `context`: effective operation, period, scope, and applicable grouping or
  time-series semantics.
- `warnings` and entity-resolution `candidates`.
- `views`: flat semantic `DataView` objects.

A view has a stable ID, a shape (`metrics`, `categorical`, or `timeseries`),
flat scalar rows, field metadata, semantic dimensions, default measures, and a
default-visibility flag. It does not name a chart library or UI component.
`DataField.format` identifies text, dates, integers, decimals, SEK currency, and
fractional percentages so clients do not infer formatting from field names.

Views emitted by each tool:

- `sales_summary`: `current` and optional `comparison`.
- `sales_rank`: `ranking`.
- `sales_trend`: `trend`.
- `product_overview`: `current`, optional `comparison`, `trend`,
  `channel_breakdown`, and `city_breakdown`.

## Supported semantics

- Metrics: units, gross sales, net sales, discounts, orders, average selling
  price, and discount rate.
- Rankings and breakdowns: product, category, store, city, and channel.
- Trend grain: day, week, month, and quarter.
- Period-over-period comparison for explicit finite periods.
- Filters: channels, cities, store IDs, categories, and canonical product IDs.

When period bounds are omitted, the full available supplier range is used. The
effective period and scope are always returned in `context`.

## Unsupported semantics

The available data cannot establish causal drivers or provide market share,
competitor performance, inventory, returns, demographics, forecasts, profit,
or margin. Agents may describe observed changes but must not present correlation
as causation.

Distinct order counts are computed at the selected analytical grain and are not
additive across entity groups. When ranking by orders, shares describe order
participation rather than mutually exclusive order ownership.
