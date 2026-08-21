import { describe, expect, it } from 'vitest'
import { performanceGroupDisplayName } from './performanceGroupDisplayName'

const labels = {
  online: 'Online',
  physical: 'Physical',
  unknown: 'Unknown',
}

describe('performanceGroupDisplayName', () => {
  it('uses the real Online city value for the online store', () => {
    expect(performanceGroupDisplayName(
      {
        group_id: 'Online',
        group_name: 'Online',
        value: 100,
      },
      'city',
      labels,
    )).toBe('Online')
  })

  it('uses Online for the online store row', () => {
    expect(performanceGroupDisplayName(
      {
        group_id: 'ONLINE-SE',
        group_name: 'Online Store',
        value: 100,
      },
      'store',
      labels,
    )).toBe('Online')
  })
})
