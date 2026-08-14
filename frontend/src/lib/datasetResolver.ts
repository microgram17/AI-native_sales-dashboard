// Resolves a VisualizationSpec's referenced dataset into flat rows and reads
// spec fields defensively. The renderer cares about visualization shape, not
// MCP tool names, so this flattens any known analytics result into rows.

import type { Dataset } from '../types/agent'

export type Row = Record<string, unknown>

const ARRAY_RESULT_KEYS = ['rows', 'trend', 'channel_breakdown', 'city_breakdown', 'candidates']

/** Find the dataset referenced by a spec; fall back to the sole dataset. */
export function findDataset(datasets: Dataset[], ref: string): Dataset | undefined {
  const byId = datasets.find((d) => d.call_id === ref)
  if (byId) return byId
  return datasets.length === 1 ? datasets[0] : undefined
}

function flattenRow(item: unknown): Row {
  if (item == null || typeof item !== 'object') return { value: item }
  const out: Row = {}
  for (const [key, value] of Object.entries(item as Row)) {
    if (value != null && typeof value === 'object' && !Array.isArray(value)) {
      // Hoist nested scalar fields (entity.name -> name, metrics.units -> units)
      for (const [nk, nv] of Object.entries(value as Row)) {
        if (out[nk] === undefined) out[nk] = nv
      }
      out[key] = value // keep nested object for dot-path access
    } else {
      out[key] = value
    }
  }
  return out
}

/** Flatten an analytics result into a list of rows for charting/tables. */
export function datasetToRows(dataset: Dataset | undefined): Row[] {
  if (!dataset) return []
  const result = dataset.result ?? {}

  for (const key of ARRAY_RESULT_KEYS) {
    const arr = (result as Row)[key]
    if (Array.isArray(arr) && arr.length > 0) return arr.map(flattenRow)
  }
  // Single-snapshot results (e.g. sales_summary.current).
  const current = (result as Row)['current']
  if (current && typeof current === 'object') return [flattenRow(current)]
  // Otherwise treat the whole result as one row.
  return Object.keys(result).length ? [flattenRow(result)] : []
}

/** Read a field from a row, tolerating dot paths and last-segment fallbacks. */
export function resolveField(row: Row, key: string | null | undefined): unknown {
  if (!key) return undefined
  if (key in row) return row[key]
  if (key.includes('.')) {
    let cur: unknown = row
    for (const part of key.split('.')) {
      if (cur == null || typeof cur !== 'object') return undefined
      cur = (cur as Row)[part]
    }
    if (cur !== undefined) return cur
  }
  const last = key.split('.').pop() as string
  return last in row ? row[last] : undefined
}

const LABEL_CANDIDATES = ['name', 'label', 'period_label', 'period_start', 'id', 'category', 'city', 'channel']

/** Pick a sensible x/category field when the spec's x_key is missing/unresolved. */
export function pickLabelKey(rows: Row[], preferred?: string | null): string {
  if (preferred && rows.some((r) => resolveField(r, preferred) !== undefined)) return preferred
  const first = rows[0] ?? {}
  for (const c of LABEL_CANDIDATES) if (c in first) return c
  const firstString = Object.keys(first).find((k) => typeof first[k] === 'string')
  return firstString ?? Object.keys(first)[0] ?? 'label'
}

/** Pick numeric value keys when the spec's y_keys are missing/unresolved. */
export function pickValueKeys(rows: Row[], preferred?: string[]): string[] {
  const usable = (preferred ?? []).filter((k) => rows.some((r) => typeof resolveField(r, k) === 'number'))
  if (usable.length) return usable
  const first = rows[0] ?? {}
  return Object.keys(first).filter(
    (k) => typeof first[k] === 'number' && !/rank/.test(k.toLowerCase()),
  )
}
