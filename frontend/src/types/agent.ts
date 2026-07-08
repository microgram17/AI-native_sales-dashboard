// ── Request ──────────────────────────────────────────────────────────────────

export interface AgentRequest {
  supplier_code: string
  question: string
}

// ── Legacy visualization types (kept for backwards compatibility) ─────────────

export interface SeriesKey {
  key: string
  name: string
}

export interface DataKeys {
  x?: string
  label?: string
  value?: string
  series?: SeriesKey[]
  columns?: string[]
}

export interface LegacyVisualization {
  type: string
  title?: string
  data_keys?: DataKeys
  data?: Record<string, unknown>[]
}

/** @deprecated Use LegacyVisualization. Kept so existing imports don't break. */
export type Visualization = LegacyVisualization

// ── New typed artifact/visualization types ────────────────────────────────────

export type ChartValueType = 'string' | 'number' | 'currency' | 'percent' | 'date'

export type VisualizationColumn = {
  key: string
  label: string
  type: ChartValueType
}

export type BaseVisualizationSpec = {
  type: 'line_chart' | 'bar_chart' | 'metric_card' | 'table'
  title?: string
  description?: string
  columns?: VisualizationColumn[]
  data: Record<string, unknown>[]
}

export type LineChartSpec = BaseVisualizationSpec & {
  type: 'line_chart'
  x_key: string
  y_keys: string[]
  series_key?: string | null
}

export type BarChartSpec = BaseVisualizationSpec & {
  type: 'bar_chart'
  x_key: string
  y_keys: string[]
  orientation?: 'vertical' | 'horizontal'
  series_key?: string | null
}

export type MetricCardSpec = BaseVisualizationSpec & {
  type: 'metric_card'
  label_key: string
  value_key: string
  sublabel_key?: string | null
}

export type TableSpec = BaseVisualizationSpec & {
  type: 'table'
  columns: VisualizationColumn[]
}

export type VisualizationSpec = LineChartSpec | BarChartSpec | MetricCardSpec | TableSpec

export type VisualizationArtifact = {
  artifact_type: 'visualization'
  id?: string
  title?: string
  source_tool?: string
  spec: VisualizationSpec
}

export type AgentArtifact = VisualizationArtifact

// ── Response / chat types ─────────────────────────────────────────────────────

export interface AgentResponse {
  answer: string
  artifacts?: AgentArtifact[]
  /** @deprecated Prefer artifacts[]. Kept for backwards compat with old backend. */
  visualization?: LegacyVisualization | null
  source?: Record<string, unknown>
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  artifacts?: AgentArtifact[]
  isError?: boolean
}
