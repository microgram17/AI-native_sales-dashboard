const SEK = new Intl.NumberFormat('sv-SE', {
  style: 'currency',
  currency: 'SEK',
  maximumFractionDigits: 0,
})

const INT = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 0 })
const DEC = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 2 })

export type MetricFamily = 'currency' | 'rate' | 'count' | 'number'

function isMonetaryKey(key: string): boolean {
  return /(sales|revenue|discount|price|sek|cost)/.test(key) && !/rate/.test(key)
}

function isRateKey(key: string): boolean {
  return /(rate|share|percent)/.test(key)
}

function isCountKey(key: string): boolean {
  return /(units|orders|count|rank|quantity)/.test(key)
}

export function metricFamily(key: string): MetricFamily {
  const k = key.toLowerCase()
  if (isRateKey(k)) return 'rate'
  if (isMonetaryKey(k)) return 'currency'
  if (isCountKey(k)) return 'count'
  return 'number'
}

export function formatMetricValue(
  key: string,
  value: unknown,
  format?: DataFieldFormat,
): string {
  if (value == null || value === '') return '—'
  if (typeof value !== 'number' || Number.isNaN(value)) return String(value)

  const family = metricFamily(key)
  if (format === 'percentage_fraction' || (!format && family === 'rate')) {
    const pct = format === 'percentage_fraction'
      ? value * 100
      : Math.abs(value) <= 1 ? value * 100 : value
    return `${DEC.format(pct)}%`
  }
  if (format === 'currency_sek' || (!format && family === 'currency')) {
    return SEK.format(value)
  }
  if (format === 'integer' || (!format && family === 'count')) return INT.format(value)
  return DEC.format(value)
}

export function humanizeKey(key: string): string {
  const cleaned = key.replace(/_/g, ' ').trim()
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
}
import type { DataFieldFormat } from '../types/agent'
