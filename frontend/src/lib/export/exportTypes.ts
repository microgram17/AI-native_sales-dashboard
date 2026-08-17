
export interface ExportColumn {
  key: string
  label: string
}

export interface ExportFilter {
  label: string
  value: unknown
}

export interface ExportPayload {
  title: string
  rows: Record<string, unknown>[]
  columns: ExportColumn[]
  filters?: ExportFilter[]
}
