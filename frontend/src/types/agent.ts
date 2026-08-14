// Types mirroring the backend agent contract (app/schemas/agent.py + visualization.py).
// The backend is the source of truth; the frontend never sends supplier identity.

export type VisualizationType = 'metric_cards' | 'bar_chart' | 'line_chart' | 'table'

export interface VisualizationSpec {
  dataset: string // call_id of the dataset this visualizes
  type: VisualizationType
  title: string
  x_key?: string | null
  y_keys: string[]
  series_key?: string | null
}

export interface ToolCallInfo {
  call_id: string
  tool_name: string
  arguments: Record<string, unknown>
  purpose?: string | null
  status?: string | null
  error?: string | null
}

// Generic JSON dataset at the API boundary; narrowed in renderer helpers.
export interface Dataset {
  call_id: string
  tool_name: string
  status: string
  result: Record<string, unknown>
}

export interface AgentQueryRequest {
  message: string
  conversation_id?: string | null
}

export interface AgentQueryResponse {
  conversation_id: string
  message: string
  tool_calls: ToolCallInfo[]
  datasets: Dataset[]
  visualizations: VisualizationSpec[]
}

// UI-side representation of one chat turn.
export interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  content: string
  visualizations?: VisualizationSpec[]
  datasets?: Dataset[]
}
