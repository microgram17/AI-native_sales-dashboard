
import {
  useRef,
  useState,
  type RefObject,
} from 'react'
import { useTranslation } from '../../i18n/LanguageContext'
import { exportNodeToPng } from '../../lib/export/exportImage'
import {
  exportToCsv,
  exportToExcel,
} from '../../lib/export/exportSpreadsheet'
import type { ExportPayload } from '../../lib/export/exportTypes'

interface ExportMenuProps extends ExportPayload {
  targetRef: RefObject<HTMLElement | null>
}

type ExportFormat = 'xlsx' | 'csv' | 'png'

export function ExportMenu({
  targetRef,
  title,
  rows,
  columns,
  filters = [],
}: ExportMenuProps) {
  const { t } = useTranslation()
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const [busyFormat, setBusyFormat] = useState<ExportFormat | null>(null)
  const [error, setError] = useState(false)

  const hasData = rows.length > 0 && columns.length > 0

  async function runExport(format: ExportFormat) {
    if (busyFormat) return

    setBusyFormat(format)
    setError(false)

    try {
      const payload = {
        title,
        rows,
        columns,
        filters,
      }

      if (format === 'xlsx') {
        if (!hasData) return
        await exportToExcel(payload, {
          dataSheetName: t.exportDataSheet,
          filtersSheetName: t.exportFiltersSheet,
          filterLabelHeading: t.exportFilter,
          filterValueHeading: t.exportValue,
        })
      } else if (format === 'csv') {
        if (!hasData) return
        await exportToCsv(payload)
      } else {
        const node = targetRef.current
        if (!node) return
        await exportNodeToPng(node, title)
      }

      detailsRef.current?.removeAttribute('open')
    } catch (exportError) {
      console.error('Visualization export failed', exportError)
      setError(true)
    } finally {
      setBusyFormat(null)
    }
  }

  return (
    <div
      className="export-control"
      data-export-control="true"
    >
      <details
        ref={detailsRef}
        className="export-menu"
      >
        <summary
          className="export-menu-trigger"
          aria-label={t.export}
          title={t.export}
        >
          {busyFormat ? t.exporting : t.export}
          <span aria-hidden="true" className="export-menu-chevron">
            ▾
          </span>
        </summary>

        <div className="export-menu-popover">
          <button
            type="button"
            disabled={!!busyFormat || !hasData}
            onClick={() => void runExport('xlsx')}
          >
            {t.exportExcel}
          </button>
          <button
            type="button"
            disabled={!!busyFormat || !hasData}
            onClick={() => void runExport('csv')}
          >
            {t.exportCsv}
          </button>
          <button
            type="button"
            disabled={!!busyFormat}
            onClick={() => void runExport('png')}
          >
            {t.exportPng}
          </button>
        </div>
      </details>

      {error && (
        <span
          role="alert"
          className="export-error"
        >
          {t.exportFailed}
        </span>
      )}
    </div>
  )
}
