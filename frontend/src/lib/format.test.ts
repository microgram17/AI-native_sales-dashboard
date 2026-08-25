import { describe, expect, it } from 'vitest'
import { formatMetricValue } from './format'

describe('formatMetricValue metadata', () => {
  it('uses declared currency formatting instead of the field name', () => {
    expect(formatMetricValue('value', 1250, 'currency_sek')).toContain('kr')
  })

  it('uses fraction percentage semantics from metadata', () => {
    expect(formatMetricValue('value', 0.125, 'percentage_fraction')).toContain('12,5')
  })

  it('uses integer formatting from metadata', () => {
    expect(formatMetricValue('value', 12.4, 'integer')).toBe('12')
  })
})
