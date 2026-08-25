import type { DataFieldFormat } from '../types/agent'

const SEK = new Intl.NumberFormat('sv-SE', {
  style: 'currency',
  currency: 'SEK',
  maximumFractionDigits: 0,
})

const INT = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 0 })
const DEC = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 2 })

export function formatMetricValue(
  value: unknown,
  format: DataFieldFormat,
): string {
  if (value == null || value === '') return '—'
  if (typeof value !== 'number' || Number.isNaN(value)) return String(value)

  if (format === 'percentage_fraction') {
    return `${DEC.format(value * 100)}%`
  }
  if (format === 'currency_sek') return SEK.format(value)
  if (format === 'integer') return INT.format(value)
  return DEC.format(value)
}
