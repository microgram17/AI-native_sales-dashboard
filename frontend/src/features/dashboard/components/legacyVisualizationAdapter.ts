import type {
  LegacyVisualization,
  VisualizationArtifact,
  VisualizationColumn,
  LineChartSpec,
  BarChartSpec,
  MetricCardSpec,
  TableSpec,
} from '../../../types/agent'

/**
 * Converts the old Visualization shape into a VisualizationArtifact.
 * This adapter is temporary — remove once all backends emit artifacts[].
 */
export function legacyVisualizationToArtifact(
  viz: LegacyVisualization,
): VisualizationArtifact | null {
  if (!viz || !viz.data?.length) return null

  const { type, title, data = [], data_keys = {} } = viz

  if (type === 'kpi_cards') {
    const labelKey = data_keys.label ?? 'metric'
    const valueKey = data_keys.value ?? 'value'
    const spec: MetricCardSpec = {
      type: 'metric_card',
      title,
      label_key: labelKey,
      value_key: valueKey,
      data,
    }
    return { artifact_type: 'visualization', spec }
  }

  if (type === 'line_chart') {
    const xKey = data_keys.x ?? 'period'
    const series = data_keys.series ?? [{ key: 'value', name: 'Value' }]
    const spec: LineChartSpec = {
      type: 'line_chart',
      title,
      x_key: xKey,
      y_keys: series.map((s) => s.key),
      data,
    }
    return { artifact_type: 'visualization', spec }
  }

  if (type === 'bar_chart') {
    const xKey = data_keys.x ?? 'name'
    const series = data_keys.series ?? [{ key: 'value', name: 'Value' }]
    const spec: BarChartSpec = {
      type: 'bar_chart',
      title,
      x_key: xKey,
      y_keys: series.map((s) => s.key),
      data,
    }
    return { artifact_type: 'visualization', spec }
  }

  if (type === 'table') {
    const cols = data_keys.columns ?? Object.keys(data[0] ?? {})
    const columns: VisualizationColumn[] = cols.map((c) => ({
      key: c,
      label: c,
      type: 'string',
    }))
    const spec: TableSpec = {
      type: 'table',
      title,
      columns,
      data,
    }
    return { artifact_type: 'visualization', spec }
  }

  return null
}
