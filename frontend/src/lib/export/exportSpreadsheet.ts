import type { WorkSheet } from 'xlsx'
import type {
  ExportColumn,
  ExportFilter,
  ExportPayload,
} from './exportTypes'
import {
  displayExportValue,
  downloadBlob,
  safeFilename,
} from './exportUtils'

function rowsToAoa(
  rows: Record<string, unknown>[],
  columns: ExportColumn[],
): Array<Array<string | number | boolean | null>> {
  const header = columns.map((column) => column.label)
  const body = rows.map((row) =>
    columns.map((column) => displayExportValue(row[column.key])),
  )

  return [header, ...body]
}

function filtersToAoa(
  filters: ExportFilter[],
  labelHeading: string,
  valueHeading: string,
): Array<Array<string | number | boolean | null>> {
  return [
    [labelHeading, valueHeading],
    ...filters.map((filter) => [
      filter.label,
      displayExportValue(filter.value),
    ]),
  ]
}

function setReasonableWidths(
  sheet: WorkSheet,
  aoa: Array<Array<string | number | boolean | null>>,
): void {
  if (aoa.length === 0) return

  const widthCount = Math.max(...aoa.map((row) => row.length))
  const widths = Array.from({ length: widthCount }, (_, columnIndex) => {
    const maxLength = aoa.reduce((max, row) => {
      const value = row[columnIndex]
      const length = value == null ? 0 : String(value).length
      return Math.max(max, length)
    }, 0)

    return {
      wch: Math.min(Math.max(maxLength + 2, 10), 48),
    }
  })

  sheet['!cols'] = widths
}

export async function exportToExcel(
  payload: ExportPayload,
  options: {
    dataSheetName: string
    filtersSheetName: string
    filterLabelHeading: string
    filterValueHeading: string
  },
): Promise<void> {
  const XLSX = await import('xlsx')

  const dataAoa = rowsToAoa(payload.rows, payload.columns)
  const dataSheet = XLSX.utils.aoa_to_sheet(dataAoa)
  setReasonableWidths(dataSheet, dataAoa)

  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(
    workbook,
    dataSheet,
    options.dataSheetName.slice(0, 31),
  )

  if (payload.filters && payload.filters.length > 0) {
    const filtersAoa = filtersToAoa(
      payload.filters,
      options.filterLabelHeading,
      options.filterValueHeading,
    )
    const filtersSheet = XLSX.utils.aoa_to_sheet(filtersAoa)
    setReasonableWidths(filtersSheet, filtersAoa)
    XLSX.utils.book_append_sheet(
      workbook,
      filtersSheet,
      options.filtersSheetName.slice(0, 31),
    )
  }

  XLSX.writeFileXLSX(
    workbook,
    `${safeFilename(payload.title)}.xlsx`,
    { compression: true },
  )
}

export async function exportToCsv(
  payload: ExportPayload,
): Promise<void> {
  const XLSX = await import('xlsx')

  const dataAoa = rowsToAoa(payload.rows, payload.columns)
  const sheet = XLSX.utils.aoa_to_sheet(dataAoa)
  const csv = XLSX.utils.sheet_to_csv(sheet)

  // UTF-8 BOM makes Swedish characters open reliably in desktop Excel.
  const blob = new Blob(['\uFEFF', csv], {
    type: 'text/csv;charset=utf-8',
  })
  downloadBlob(blob, `${safeFilename(payload.title)}.csv`)
}
