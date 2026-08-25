
import { describe, expect, it } from 'vitest'
import {
  displayExportValue,
  safeFilename,
} from './exportUtils'

describe('exportUtils', () => {
  it('creates filesystem-safe filenames without dropping Swedish letters', () => {
    expect(
      safeFilename('Försäljning: Q1 / Sverige?'),
    ).toBe('Försäljning-Q1-Sverige')
  })

  it('keeps primitive spreadsheet values and serializes complex values', () => {
    expect(displayExportValue(42)).toBe(42)
    expect(displayExportValue('hello')).toBe('hello')
    expect(displayExportValue(['a', 'b'])).toBe('a, b')
    expect(displayExportValue({ channel: 'online' })).toBe(
      '{"channel":"online"}',
    )
  })
})
