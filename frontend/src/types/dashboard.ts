export interface DashboardUser {
  user_id: string
  display_name: string
  supplier_id: string
}

export interface KpiCardData {
  key: string
  label: string
  value: number
  unit: string | null
}

export interface DashboardArtifact {
  source_tool: string
  result_type: string
  title: string
  description?: string
  columns: Array<Record<string, unknown>>
  rows: Array<Record<string, unknown>>
  recommended_visualizations?: Array<Record<string, unknown>>
  data_quality?: Record<string, unknown>
}

export interface DashboardResponse {
  user: DashboardUser
  cards: KpiCardData[]
  artifacts: DashboardArtifact[]
}
