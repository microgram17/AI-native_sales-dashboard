import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import type { ChatEntry } from '../../types/agent'
import { queryAgent } from '../../api/agent'
import { ChatMessage } from './ChatMessage'
import { useTranslation } from '../../i18n/LanguageContext'

export function ChatPanel() {
  const { t, language } = useTranslation()
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({
    mutationFn: queryAgent,
    onSuccess: (data) => {
      setConversationId(data.conversation_id)
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.message,
          visualizations: data.visualizations,
          visualizationDatasets: data.visualization_datasets,
        },
      ])
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || mutation.isPending) return

    setInput('')
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: text },
    ])
    mutation.mutate({
      message: text,
      conversation_id: conversationId,
      language,
    })
  }

  function handleNewConversation() {
    if (mutation.isPending) return
    setMessages([])
    setConversationId(null)
    mutation.reset()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '560px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          padding: '0.4rem 1rem',
          borderBottom: '1px solid var(--border, #334155)',
        }}
      >
        <button
          type="button"
          onClick={handleNewConversation}
          disabled={mutation.isPending || messages.length === 0}
          style={{
            padding: '0.3rem 0.75rem',
            borderRadius: '6px',
            border: '1px solid var(--border, #334155)',
            background: 'transparent',
            color: 'inherit',
            fontSize: '0.8rem',
            cursor: mutation.isPending || messages.length === 0 ? 'not-allowed' : 'pointer',
            opacity: mutation.isPending || messages.length === 0 ? 0.5 : 1,
          }}
        >
          {t.newConversation}
        </button>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              color: 'var(--muted)',
              fontSize: '0.875rem',
              marginTop: '2rem',
            }}
          >
            {t.chatEmpty}
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            role={msg.role}
            content={msg.content}
            visualizations={msg.visualizations}
            visualizationDatasets={msg.visualizationDatasets}
          />
        ))}

        {mutation.isPending && (
          <div
            style={{
              color: 'var(--muted)',
              fontSize: '0.8rem',
              fontStyle: 'italic',
              marginBottom: '0.5rem',
              alignSelf: 'flex-start',
            }}
          >
            {t.chatThinking}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {mutation.isError && (
        <div
          role="alert"
          style={{
            padding: '0.5rem 1rem',
            fontSize: '0.8rem',
            color: '#f87171',
            background: 'rgba(248,113,113,0.08)',
            borderTop: '1px solid rgba(248,113,113,0.2)',
          }}
        >
          {mutation.error instanceof Error ? mutation.error.message : t.chatError}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          gap: '0.5rem',
          padding: '0.75rem 1rem',
          borderTop: '1px solid var(--border, #334155)',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t.chatPlaceholder}
          disabled={mutation.isPending}
          style={{
            flex: 1,
            padding: '0.5rem 0.75rem',
            borderRadius: '6px',
            border: '1px solid var(--border, #334155)',
            background: 'var(--surface, #1e293b)',
            color: 'inherit',
            fontSize: '0.875rem',
            outline: 'none',
          }}
        />
        <button
          type="submit"
          disabled={mutation.isPending || !input.trim()}
          style={{
            padding: '0.5rem 1.125rem',
            borderRadius: '6px',
            border: 'none',
            background: 'var(--accent, #6366f1)',
            color: '#fff',
            fontSize: '0.875rem',
            cursor: mutation.isPending || !input.trim() ? 'not-allowed' : 'pointer',
            opacity: mutation.isPending || !input.trim() ? 0.55 : 1,
            transition: 'opacity 0.15s',
          }}
        >
          {mutation.isPending ? '…' : t.chatSend}
        </button>
      </form>
    </div>
  )
}
