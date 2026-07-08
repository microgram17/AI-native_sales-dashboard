interface TopProductsTableProps {
  rows: Array<Record<string, unknown>>
  loading: boolean
}

const fmtSEK = (n: number) =>
  new Intl.NumberFormat('sv-SE', {
    style: 'currency',
    currency: 'SEK',
    maximumFractionDigits: 0,
  }).format(n)

export function TopProductsTable({ rows, loading }: TopProductsTableProps) {
  if (loading) return <div className="table-placeholder">Loading…</div>
  if (!rows.length)
    return <div className="table-placeholder">No products found.</div>

  return (
    <table className="products-table">
      <thead>
        <tr>
          <th className="num">#</th>
          <th>Product</th>
          <th>Category</th>
          <th className="num">Net Sales</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={String(row.product_id ?? i)}>
            <td className="num secondary">{String(row.rank ?? i + 1)}</td>
            <td>{String(row.product_name ?? '')}</td>
            <td className="secondary">{String(row.category ?? '')}</td>
            <td className="num">
              {typeof row.value === 'number' ? fmtSEK(row.value) : String(row.value ?? '—')}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
