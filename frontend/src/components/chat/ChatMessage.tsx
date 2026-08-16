import type {
  VisualizationDataset,
  VisualizationSpec,
} from '../../types/agent'
import { VisualizationRenderer } from '../visualizations/VisualizationRenderer'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  visualizations?: VisualizationSpec[]
  visualizationDatasets?: VisualizationDataset[]
}

export function ChatMessage({
  role,
  content,
  visualizations,
  visualizationDatasets,
}: ChatMessageProps) {
  if (role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.75rem' }}>
        <div
          style={{
            background: 'var(--accent, #6366f1)',
            color: '#fff',
            borderRadius: '12px 12px 2px 12px',
            padding: '0.5rem 0.875rem',
            maxWidth: '75%',
            fontSize: '0.875rem',
            lineHeight: 1.5,
            wordBreak: 'break-word',
          }}
        >
          {content}
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', marginBottom: '0.75rem' }}>
      <div
        style={{
          background: 'rgba(51,65,85,0.5)',
          borderRadius: '2px 12px 12px 12px',
          padding: '0.5rem 0.875rem',
          fontSize: '0.875rem',
          lineHeight: 1.5,
          alignSelf: 'flex-start',
          maxWidth: '90%',
          wordBreak: 'break-word',
          whiteSpace: 'pre-wrap',
        }}
      >
        {content}
      </div>

      {visualizations && visualizations.length > 0 && (
        <div style={{ width: '100%', maxWidth: '640px' }}>
          <VisualizationRenderer
            visualizations={visualizations}
            datasets={visualizationDatasets ?? []}
          />
        </div>
      )}
    </div>
  )
}
