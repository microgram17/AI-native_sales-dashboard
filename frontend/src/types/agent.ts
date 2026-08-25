export type UiLanguage = 'en' | 'sv'

export type DataFieldFormat =
  | 'text'
  | 'date'
  | 'integer'
  | 'decimal'
  | 'currency_sek'
  | 'percentage_fraction'

export interface DataField {
  key: string
  role: 'dimension' | 'measure'
  format: DataFieldFormat
}

export interface DataView {
  id: string
  kind: 'metrics' | 'categorical' | 'timeseries'
  rows: Record<string, unknown>[]
  fields: DataField[]
  primary_dimension?: string | null
  series_dimension?: string | null
  default_measures: string[]
  default_visible: boolean
}

export interface EffectivePeriod {
  start: string
  end: string
  label?: string | null
  defaulted: boolean
}

export interface AnalyticsContext {
  operation: 'summary' | 'ranking' | 'trend' | 'product_overview'
  effective_period: EffectivePeriod
  effective_scope: WidgetAnalysisScope & { product_ids?: string[] }
  grain?: 'day' | 'week' | 'month' | 'quarter' | null
  group_by?: 'product' | 'category' | 'store' | 'city' | 'channel' | null
  rank_by?: string | null
  order?: 'highest' | 'lowest' | null
  split_by?: 'product' | 'category' | 'store' | 'city' | 'channel' | null
  entity?: { type: string; id?: string | null; name: string } | null
}

export interface DisplaySelection {
  view_id: string
  render_as: 'default' | 'table'
  measure_keys: string[]
  title?: string | null
}

export interface ToolCallInfo {
  call_id: string
  tool_name: string
  arguments: Record<string, unknown>
  status?: string | null
  error?: string | null
}

export interface DashboardChatContext {
  date_from: string
  date_to: string
  metric?: string
  grain?: string
  group_by?: string
  view?: string
  selected_group_ids?: string[]
}

export interface WidgetAnalysisScope {
  channels?: Array<'online' | 'physical'>
  cities?: string[]
  store_ids?: string[]
  categories?: string[]
}

export interface WidgetAnalysisRequest {
  widget: 'kpi' | 'sales_trend' | 'performance'
  operation: 'summary' | 'trend' | 'ranking'
  metrics: string[]
  period_start: string
  period_end: string
  grain?: 'day' | 'week' | 'month' | 'quarter'
  group_by?: 'product' | 'category' | 'store' | 'city' | 'channel'
  rank_by?: 'units' | 'net_sales' | 'gross_sales' | 'discounts' | 'orders'
  split_by?: 'product' | 'category' | 'store' | 'city' | 'channel'
  limit?: number
  series_limit?: number
  scope?: WidgetAnalysisScope
}

export interface AgentQueryRequest {
  message: string
  conversation_id?: string | null
  language: UiLanguage
  dashboard_context?: DashboardChatContext
  widget_analysis?: WidgetAnalysisRequest
}

export interface AgentQueryResponse {
  conversation_id: string
  message: string
  tool_calls: ToolCallInfo[]
  data_context?: AnalyticsContext | null
  data_views: DataView[]
  displays: DisplaySelection[]
}

export interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  content: string
  displays?: DisplaySelection[]
  dataViews?: DataView[]
  dataContext?: AnalyticsContext | null
  toolCalls?: ToolCallInfo[]
}

// Internal renderer adapter contracts. These are not part of the HTTP API.
export type VisualizationType = 'metric_cards' | 'bar_chart' | 'line_chart' | 'table'

export interface VisualizationSpec {
  dataset: string
  type: VisualizationType
  title: string
  x_key?: string | null
  y_keys: string[]
  secondary_y_keys?: string[]
  selectable_y_keys?: string[]
  series_key?: string | null
  columns: string[]
}

export interface VisualizationDataset extends DataView {
  source_call_id: string
  view: string
}
