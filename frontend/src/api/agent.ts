import { apiFetch } from './client'
import type { AgentRequest, AgentResponse } from '../types/agent'

export const agentApi = {
  ask: (request: AgentRequest) =>
    apiFetch<AgentResponse>('/api/agent/ask', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
}
