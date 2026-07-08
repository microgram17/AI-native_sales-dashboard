import type { Metric, TopProductsRow } from '../../../types/dashboard'

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

const COLUMNS: { key: Metric; label: string; format: (v: number) => string }[] = [
  { key: 'net_sales', label: 'Net Sales', format: fmtSEK },
  { key: 'gross_sales', label: 'Gross Sales', format: fmtSEK },
  { key: 'units', label: 'Units', format: fmtInt },
  { key: 'orders', label: 'Orders', format: fmtInt },
  { key: 'discounts', label: 'Discounts', format: fmtSEK },
]

export function TopProductsTable({ rows, loading, sortBy, onSortByChange }: TopProductsTableProps) {
  if (loading) return <div className="table-placeholder">Loading…</div>
  if (!rows.length) return <div className="table-placeholder">No products found.</div>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="products-table">
        <thead>
          <tr>
            <th className="num">#</th>
            <th>Product</th>
            <th>Category</th>
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
                title={`Sort by ${col.label}`}
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
