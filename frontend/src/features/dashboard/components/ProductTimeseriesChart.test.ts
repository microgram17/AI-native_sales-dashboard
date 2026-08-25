import { describe, expect, it } from 'vitest'
import type { ProductSelectorItem } from '../../../types/dashboard'
import { stableProductColor } from './productSeriesColor'
import { COLORS } from './visualizationUtils'

function product(
  productId: string,
  productName: string,
): ProductSelectorItem {
  return {
    product_id: productId,
    product_name: productName,
    category: 'Test',
    net_sales: 0,
    units: 0,
  }
}

describe('stableProductColor', () => {
  const products = [
    product('product-1', 'Product 1'),
    product('product-2', 'Product 2'),
    product('product-3', 'Product 3'),
    product('product-4', 'Product 4'),
    product('product-5', 'Product 5'),
    product('product-6', 'Product 6'),
  ]
  const selectedProductIds = products.map(
    (item) => item.product_id,
  )

  it('assigns contrasting palette entries by selection order', () => {
    const colors = products.map((item) =>
      stableProductColor(
        item.product_name,
        products,
        selectedProductIds,
      ),
    )

    expect(new Set(colors)).toHaveLength(products.length)
    expect(colors[0]).toBe(COLORS[0])
    expect(colors[5]).toBe(COLORS[5])
  })

  it('keeps colors stable when the product catalog is reordered', () => {
    const color = stableProductColor(
      'Product 6',
      products,
      selectedProductIds,
    )

    expect(
      stableProductColor(
        'Product 6',
        [...products].reverse(),
        selectedProductIds,
      ),
    ).toBe(color)
  })
})
