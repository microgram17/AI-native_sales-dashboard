export const COLORS = ['var(--accent)', '#94a3b8', '#64748b', '#e2a03f']

export function formatShortNumber(v: unknown): string {
  if (typeof v !== 'number') return String(v ?? '')
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(0)}k`
  return new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 1 }).format(v)
}

export function formatTooltipValue(v: unknown): string {
  if (typeof v !== 'number') return String(v ?? '')
  return new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 0 }).format(v)
}

/**
 * Transform long-form rows into wide-form rows for series-based charts.
 *
 * @example
 * // Input: [{ month: '2026-01', product: 'A', revenue: 100 }, ...]
 * // with xKey='month', seriesKey='product', yKey='revenue'
 * // Output: { wideData: [{ month: '2026-01', A: 100, B: 200 }], seriesValues: ['A', 'B'] }
 */
export function longToWide(
  data: Record<string, unknown>[],
  xKey: string,
  seriesKey: string,
  yKey: string,
): { wideData: Record<string, unknown>[]; seriesValues: string[] } {
  const rowMap = new Map<unknown, Record<string, unknown>>()
  const seriesSet = new Set<string>()

  for (const row of data) {
    const xVal = row[xKey]
    const seriesVal = String(row[seriesKey] ?? '')
    const yVal = row[yKey]
    seriesSet.add(seriesVal)

    if (!rowMap.has(xVal)) {
      rowMap.set(xVal, { [xKey]: xVal })
    }
    const wideRow = rowMap.get(xVal)!
    wideRow[seriesVal] = yVal
  }

  return {
    wideData: Array.from(rowMap.values()),
    seriesValues: Array.from(seriesSet),
  }
}
