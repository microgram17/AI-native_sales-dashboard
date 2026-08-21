import ReactMarkdown from 'react-markdown'
import type {
  VisualizationDataset,
  VisualizationSpec,
  ToolCallInfo,
} from '../../types/agent'
import { VisualizationRenderer } from '../visualizations/VisualizationRenderer'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  visualizations?: VisualizationSpec[]
  visualizationDatasets?: VisualizationDataset[]
  toolCalls?: ToolCallInfo[]
}

export function ChatMessage({
  role,
  content,
  visualizations,
  visualizationDatasets,
  toolCalls,
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

  const hasVisualizations =
    Array.isArray(visualizations) && visualizations.length > 0

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
              visualizations={visualizations}
              datasets={visualizationDatasets ?? []}
              toolCalls={toolCalls ?? []}
            />
          </div>
        )}
      </div>
    </div>
  )
}
