import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { agentApi } from '../../../api/agent'
import type { AgentArtifact, ChatMessage } from '../../../types/agent'
import { legacyVisualizationToArtifact } from './legacyVisualizationAdapter'
import { ArtifactRenderer } from './ArtifactRenderer'

interface AgentChatProps {
  supplierCode: string
}

export function AgentChat({ supplierCode }: AgentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  // Clear history when the supplier changes
  useEffect(() => {
    setMessages([])
  }, [supplierCode])

  // Scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const mutation = useMutation({
    mutationFn: (question: string) =>
      agentApi.ask({ supplier_code: supplierCode, question }),
    onSuccess: (data) => {
      let artifacts: AgentArtifact[] = data.artifacts ?? []
      if (artifacts.length === 0 && data.visualization) {
        const adapted = legacyVisualizationToArtifact(data.visualization)
        if (adapted) artifacts = [adapted]
      }
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.answer,
          artifacts,
        },
      ])
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Something went wrong. Please try again.',
          isError: true,
        },
      ])
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = input.trim()
    if (!q || mutation.isPending) return
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: q },
    ])
    setInput('')
    mutation.mutate(q)
  }

  return (
    <div className="agent-chat">
      <div className="agent-chat-messages">
        {messages.length === 0 && (
          <p className="agent-chat-empty">
            Ask a question about the selected supplier — revenue, top products,
            market share, and more.
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`message message-${msg.role}`}>
            <div className={`message-bubble${msg.isError ? ' message-error' : ''}`}>
              {msg.content}
              {msg.role === 'assistant' &&
                msg.artifacts &&
                msg.artifacts.length > 0 && (
                  <div className="message-artifacts">
                    {msg.artifacts.map((artifact, i) => (
                      <ArtifactRenderer key={artifact.id ?? i} artifact={artifact} />
                    ))}
                  </div>
                )}
            </div>
          </div>
        ))}
        {mutation.isPending && (
          <div className="message message-assistant">
            <div className="message-bubble">
              <span className="typing-dots">
                <span />
                <span />
                <span />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="agent-chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about revenue, top products, market share…"
          disabled={mutation.isPending}
          autoComplete="off"
        />
        <button type="submit" disabled={!input.trim() || mutation.isPending}>
          Send
        </button>
      </form>
    </div>
  )
}
