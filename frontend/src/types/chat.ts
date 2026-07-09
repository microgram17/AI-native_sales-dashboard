import type { DashboardArtifact } from './dashboard'

export interface ChatRequest {
  session_id?: string | null
  message: string
}

export interface ChatResponse {
  session_id: string
  assistant_message: string
  tools_used: string[]
  artifacts: DashboardArtifact[]
}
