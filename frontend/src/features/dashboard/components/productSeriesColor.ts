import type { ProductSelectorItem } from '../../../types/dashboard'
import { COLORS } from './visualizationUtils'

export function stableProductColor(
  productName: string,
  products: ProductSelectorItem[],
  selectedProductIds: string[],
): string {
  const product = products.find(
    (item) => item.product_name === productName,
  )
  const selectedIndex = product
    ? selectedProductIds.indexOf(product.product_id)
    : -1
  const fallbackIndex = products.findIndex(
    (item) => item.product_name === productName,
  )
  const colorIndex = selectedIndex >= 0
    ? selectedIndex
    : Math.max(fallbackIndex, 0)

  return COLORS[colorIndex % COLORS.length]
}
