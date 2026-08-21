import type {
  Metric,
  ProductSortDirection,
  TopProductsRow,
} from '../../../types/dashboard'
import { useTranslation } from '../../../i18n/LanguageContext'

interface TopProductsTableProps {
  rows: TopProductsRow[]
  loading: boolean
  sortBy: Metric
  sortDirection: ProductSortDirection
  onSortChange: (metric: Metric, direction: ProductSortDirection) => void
  hasMore: boolean
  loadingMore: boolean
  total: number
  onLoadMore: () => void
}

const fmtSEK = (n: number) =>
  new Intl.NumberFormat('sv-SE', {
    style: 'currency',
    currency: 'SEK',
    maximumFractionDigits: 0,
  }).format(n)

const fmtInt = (n: number) =>
  new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 0 }).format(n)

export function TopProductsTable({
  rows,
  loading,
  sortBy,
  sortDirection,
  onSortChange,
  hasMore,
  loadingMore,
  total,
  onLoadMore,
}: TopProductsTableProps) {
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
    <div
      className="top-products-table-scroll"
      onScroll={(event) => {
        const element = event.currentTarget
        const nearBottom =
          element.scrollHeight - element.scrollTop - element.clientHeight < 80
        if (nearBottom && hasMore && !loadingMore) {
          onLoadMore()
        }
      }}
    >
      <table className="products-table">
        <thead>
          <tr>
            <th className="num">#</th>
            <th>{t.colProduct}</th>
            <th>{t.colCategory}</th>
            {COLUMNS.map((column) => (
              <th
                key={column.key}
                className="num"
                aria-sort={
                  sortBy === column.key
                    ? sortDirection === 'desc'
                      ? 'descending'
                      : 'ascending'
                    : 'none'
                }
              >
                <button
                  type="button"
                  className={sortBy === column.key ? 'active' : ''}
                  onClick={() => onSortChange(
                    column.key,
                    sortBy === column.key && sortDirection === 'desc'
                      ? 'asc'
                      : 'desc',
                  )}
                  title={t.sortBy(column.label)}
                >
                  {column.label}
                  {sortBy === column.key
                    ? sortDirection === 'desc' ? ' ↓' : ' ↑'
                    : ''}
                </button>
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
              {COLUMNS.map((column) => (
                <td
                  key={column.key}
                  className={`num${sortBy === column.key ? ' sorted' : ''}`}
                >
                  {column.format(row[column.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
          <tfoot>
            <tr>
              <td colSpan={COLUMNS.length + 3}>
                {loadingMore
                  ? t.loadingMoreProducts
                  : t.productsLoaded(rows.length, total)}
              </td>
            </tr>
          </tfoot>
        </table>
    </div>
  )
}
