import type { ProductResult } from '../../../types/dashboard'

interface TopProductsTableProps {
  products: ProductResult[]
  loading: boolean
}

const fmt = (n: number) =>
  n.toLocaleString('sv-SE', { maximumFractionDigits: 0 }) + ' kr'

export function TopProductsTable({ products, loading }: TopProductsTableProps) {
  if (loading) return <div className="table-placeholder">Loading…</div>
  if (!products.length)
    return <div className="table-placeholder">No products found.</div>

  return (
    <table className="products-table">
      <thead>
        <tr>
          <th>Product</th>
          <th>Category</th>
          <th className="num">Revenue</th>
          <th className="num">Units</th>
        </tr>
      </thead>
      <tbody>
        {products.map((p) => (
          <tr key={p.sku}>
            <td>{p.product_name}</td>
            <td className="secondary">{p.category}</td>
            <td className="num">{fmt(p.total_revenue)}</td>
            <td className="num">{p.total_units.toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
