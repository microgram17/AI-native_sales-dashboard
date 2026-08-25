import { apiFetch } from './client'
import type { AgentQueryRequest, AgentQueryResponse } from '../types/agent'

// Single entry point for the agent. Supplier identity is resolved by the
// backend from the authenticated Bearer token; the frontend never sends it.
export function queryAgent(request: AgentQueryRequest): Promise<AgentQueryResponse> {
  return apiFetch<AgentQueryResponse>('/agent/query', {
    method: 'POST',
    body: JSON.stringify({
      message: request.message,
      conversation_id: request.conversation_id ?? null,
      language: request.language,
      dashboard_context: request.dashboard_context,
      widget_analysis: request.widget_analysis,
    }),
  })
}
