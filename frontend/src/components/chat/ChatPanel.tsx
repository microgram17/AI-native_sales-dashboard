import {
  useEffect,
  useRef,
  useState,
} from 'react'
import { useMutation } from '@tanstack/react-query'
import type { ChatEntry } from '../../types/agent'
import { queryAgent } from '../../api/agent'
import { ChatMessage } from './ChatMessage'
import { useTranslation } from '../../i18n/LanguageContext'

export function ChatPanel() {
  const { t, language } = useTranslation()
  const [messages, setMessages] =
    useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const [
    conversationId,
    setConversationId,
  ] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({
    mutationFn: queryAgent,
    onSuccess: (data) => {
      setConversationId(data.conversation_id)
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.message,
          visualizations:
            data.visualizations,
          visualizationDatasets:
            data.visualization_datasets,
          toolCalls: data.tool_calls,
        },
      ])
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
    })
  }, [messages])

  function handleSubmit(
    event: React.FormEvent,
  ) {
    event.preventDefault()

    const text = input.trim()
    if (!text || mutation.isPending) return

    setInput('')
    setMessages((previous) => [
      ...previous,
      {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
      },
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
    <div className="dashboard-chat">
      <div className="dashboard-chat-toolbar">
        <button
          type="button"
          onClick={handleNewConversation}
          disabled={
            mutation.isPending ||
            messages.length === 0
          }
        >
          {t.newConversation}
        </button>
      </div>

      <div className="dashboard-chat-messages">
        {messages.length === 0 && (
          <div className="dashboard-chat-empty">
            {t.chatEmpty}
          </div>
        )}

        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            role={message.role}
            content={message.content}
            visualizations={
              message.visualizations
            }
            visualizationDatasets={
              message.visualizationDatasets
            }
            toolCalls={message.toolCalls}
          />
        ))}

        {mutation.isPending && (
          <div className="dashboard-chat-thinking">
            {t.chatThinking}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {mutation.isError && (
        <div
          role="alert"
          className="dashboard-chat-error"
        >
          {mutation.error instanceof Error
            ? mutation.error.message
            : t.chatError}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="dashboard-chat-input"
      >
        <input
          type="text"
          value={input}
          onChange={(event) =>
            setInput(event.target.value)
          }
          placeholder={t.chatPlaceholder}
          disabled={mutation.isPending}
        />

        <button
          type="submit"
          disabled={
            mutation.isPending ||
            !input.trim()
          }
        >
          {mutation.isPending
            ? '…'
            : t.chatSend}
        </button>
      </form>
    </div>
  )
}
