export interface AgentRequest {
  supplier_code: string
  question: string
}

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

export interface Visualization {
  type: string
  title?: string
  data_keys?: DataKeys
  data?: Record<string, unknown>[]
}

export interface AgentResponse {
  answer: string
  visualization: Visualization
  source: Record<string, unknown>
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  visualization?: Visualization
  isError?: boolean
}
