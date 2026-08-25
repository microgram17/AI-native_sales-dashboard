import type {
  StoreBreakdownRow,
  StoreGroupBy,
} from '../../../types/dashboard'

interface GroupDisplayLabels {
  online: string
  physical: string
  unknown: string
}

export function performanceGroupDisplayName(
  row: StoreBreakdownRow,
  groupBy: StoreGroupBy,
  labels: GroupDisplayLabels,
): string {
  const rawName = row.group_name?.trim()
  const rawId = row.group_id?.trim()
  const onlineGroup =
    /^online(?:\s+store)?$/i.test(rawName ?? '') ||
    /^online(?:-se)?$/i.test(rawId ?? '')

  if (onlineGroup) {
    return labels.online
  }

  const displayName = rawName || rawId
  if (groupBy === 'channel') {
    if (/^online$/i.test(displayName ?? '')) return labels.online
    if (/^physical$/i.test(displayName ?? '')) return labels.physical
  }

  return displayName || labels.unknown
}
