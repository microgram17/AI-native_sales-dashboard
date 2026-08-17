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

export function formatMetricValue(key: string, value: unknown): string {
  if (value == null || value === '') return '—'
  if (typeof value !== 'number' || Number.isNaN(value)) return String(value)

  const family = metricFamily(key)
  if (family === 'rate') {
    const pct = Math.abs(value) <= 1 ? value * 100 : value
    return `${DEC.format(pct)}%`
  }
  if (family === 'currency') return SEK.format(value)
  if (family === 'count') return INT.format(value)
  return DEC.format(value)
}

export function humanizeKey(key: string): string {
  const cleaned = key.replace(/_/g, ' ').trim()
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
}
