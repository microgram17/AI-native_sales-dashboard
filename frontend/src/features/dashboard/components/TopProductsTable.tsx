import type { Metric, TopProductsRow } from '../../../types/dashboard'
import { useTranslation } from '../../../i18n/LanguageContext'

interface TopProductsTableProps {
  rows: TopProductsRow[]
  loading: boolean
  sortBy: Metric
  onSortByChange: (m: Metric) => void
}

const fmtSEK = (n: number) =>
  new Intl.NumberFormat('sv-SE', {
    style: 'currency',
    currency: 'SEK',
    maximumFractionDigits: 0,
  }).format(n)

const fmtInt = (n: number) =>
  new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 0 }).format(n)

export function TopProductsTable({ rows, loading, sortBy, onSortByChange }: TopProductsTableProps) {
  const { t } = useTranslation()

  const COLUMNS: { key: Metric; label: string; format: (v: number) => string }[] = [
    { key: 'net_sales', label: t.netSales, format: fmtSEK },
    { key: 'gross_sales', label: t.grossSales, format: fmtSEK },
    { key: 'units', label: t.units, format: fmtInt },
    { key: 'orders', label: t.orders, format: fmtInt },
    { key: 'discounts', label: t.discounts, format: fmtSEK },
  ]

  if (loading) return <div className="table-placeholder">{t.loading}</div>
  if (!rows.length) return <div className="table-placeholder">{t.noProducts}</div>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="products-table">
        <thead>
          <tr>
            <th className="num">#</th>
            <th>{t.colProduct}</th>
            <th>{t.colCategory}</th>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className="num"
                onClick={() => onSortByChange(col.key)}
                style={{
                  cursor: 'pointer',
                  color: sortBy === col.key ? 'var(--accent)' : undefined,
                  userSelect: 'none',
                  whiteSpace: 'nowrap',
                }}
                title={t.sortBy(col.label)}
              >
                {col.label}{sortBy === col.key ? ' ↓' : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.product_id ?? i}>
              <td className="num secondary">{row.rank}</td>
              <td>{row.product_name}</td>
              <td className="secondary">{row.category}</td>
              {COLUMNS.map((col) => (
                <td
                  key={col.key}
                  className="num"
                  style={{ fontWeight: sortBy === col.key ? 600 : undefined }}
                >
                  {col.format(row[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
