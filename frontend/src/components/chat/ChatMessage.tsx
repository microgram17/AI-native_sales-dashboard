import ReactMarkdown from 'react-markdown'
import type {
  AnalyticsContext,
  DataView,
  DisplaySelection,
  ToolCallInfo,
} from '../../types/agent'
import { VisualizationRenderer } from '../visualizations/VisualizationRenderer'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  displays?: DisplaySelection[]
  dataViews?: DataView[]
  dataContext?: AnalyticsContext | null
  toolCalls?: ToolCallInfo[]
}

export function ChatMessage({
  role,
  content,
  displays,
  dataViews,
  dataContext,
}: ChatMessageProps) {
  if (role === 'user') {
    return (
      <div className="message message-user">
        <div className="message-bubble">
          {content}
        </div>
      </div>
    )
  }

  const hasVisualizations = Array.isArray(displays) && displays.length > 0

  return (
    <div className="message message-assistant">
      <div
        className={[
          'message-bubble',
          'assistant-message-bubble',
          hasVisualizations ? 'has-visualizations' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {content && (
          <div className="assistant-message-text">
            <ReactMarkdown
              skipHtml
              components={{
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    {children}
                  </a>
                ),
                img: () => null,
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {hasVisualizations && (
          <div className="assistant-message-visualizations">
            <VisualizationRenderer
              displays={displays ?? []}
              dataViews={dataViews ?? []}
              dataContext={dataContext}
            />
          </div>
        )}
      </div>
    </div>
  )
}
