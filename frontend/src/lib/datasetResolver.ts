import type { VisualizationDataset } from '../types/agent'

export type Row = Record<string, unknown>

export function findDataset(
  datasets: VisualizationDataset[],
  ref: string,
): VisualizationDataset | undefined {
  return datasets.find((dataset) => dataset.id === ref)
}

export function datasetToRows(dataset: VisualizationDataset | undefined): Row[] {
  return dataset?.rows ?? []
}

export function resolveField(
  row: Row,
  key: string | null | undefined,
): unknown {
  if (!key) return undefined
  return row[key]
}

export function fieldExists(
  rows: Row[],
  key: string | null | undefined,
): boolean {
  if (!key) return false
  return rows.some((row) => row[key] !== undefined && row[key] !== null)
}

export function numericFieldExists(rows: Row[], key: string): boolean {
  const values = rows
    .map((row) => row[key])
    .filter((value) => value !== undefined && value !== null)

  return (
    values.length > 0 &&
    values.every(
      (value) => typeof value === 'number' && !Number.isNaN(value),
    )
  )
}
