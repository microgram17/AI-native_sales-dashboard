export type VisualizationType = 'metric_cards' | 'bar_chart' | 'line_chart' | 'table'

export interface VisualizationSpec {
  dataset: string
  type: VisualizationType
  title: string
  x_key?: string | null
  y_keys: string[]
  /**
   * Subset of y_keys rendered against the secondary/right Y axis.
   * Empty/undefined means a normal single-axis visualization.
   */
  secondary_y_keys?: string[]
  /** Metrics that can be selected locally without another agent request. */
  selectable_y_keys?: string[]
  series_key?: string | null
  columns: string[]
}

export interface VisualizationDataset {
  id: string
  source_call_id: string
  view: string
  rows: Record<string, unknown>[]
}

export interface ToolCallInfo {
  call_id: string
  tool_name: string
  arguments: Record<string, unknown>
  purpose?: string | null
  status?: string | null
  error?: string | null
}

export interface Dataset {
  call_id: string
  tool_name: string
  status: string
  result: Record<string, unknown>
}

export type UiLanguage = 'en' | 'sv'

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
  datasets: Dataset[]
  visualization_datasets: VisualizationDataset[]
  visualizations: VisualizationSpec[]
}

export interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  content: string
  visualizations?: VisualizationSpec[]
  visualizationDatasets?: VisualizationDataset[]
  toolCalls?: ToolCallInfo[]
}
