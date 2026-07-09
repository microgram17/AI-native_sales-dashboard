import { apiFetch } from './client'
import type { ChatRequest, ChatResponse } from '../types/chat'

export function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
