import type { AgentArtifact } from '../../../types/agent'
import { VisualizationRenderer } from './VisualizationRenderer'

interface Props {
  artifact: AgentArtifact
}

export function ArtifactRenderer({ artifact }: Props) {
  switch (artifact.artifact_type) {
    case 'visualization':
      return <VisualizationRenderer spec={artifact.spec} />
    default:
      return null
  }
}
