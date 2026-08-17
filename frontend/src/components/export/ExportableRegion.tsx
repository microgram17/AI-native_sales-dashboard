
import {
  useRef,
  type CSSProperties,
  type ReactNode,
} from 'react'
import { ExportMenu } from './ExportMenu'
import type {
  ExportColumn,
  ExportFilter,
} from '../../lib/export/exportTypes'

interface ExportableRegionProps {
  title: string
  rows: Record<string, unknown>[]
  columns: ExportColumn[]
  filters?: ExportFilter[]
  children: ReactNode
  className?: string
  style?: CSSProperties
}

export function ExportableRegion({
  title,
  rows,
  columns,
  filters = [],
  children,
  className,
  style,
}: ExportableRegionProps) {
  const targetRef = useRef<HTMLElement>(null)

  return (
    <section
      ref={targetRef}
      className={className}
      style={style}
    >
      <div className="exportable-region-header">
        <h2>{title}</h2>
        <ExportMenu
          targetRef={targetRef}
          title={title}
          rows={rows}
          columns={columns}
          filters={filters}
        />
      </div>

      {children}
    </section>
  )
}
