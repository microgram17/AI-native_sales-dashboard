export interface SupplierInfo {
  supplier_code: string
  supplier_name: string
  primary_brand: string | null
  primary_category: string | null
}

export interface SuppliersResponse {
  count: number
  suppliers: SupplierInfo[]
}

export interface MarketShare {
  period: string
  estimated_market_share_pct: number
}

export interface SupplierSummary {
  supplier_code: string
  supplier_name: string
  found: boolean
  message?: string
  total_orders: number
  total_units: number
  total_revenue: number
  estimated_margin: number
  average_order_value: number
  latest_market_share: MarketShare | null
}

export interface RevenueTrendPoint {
  period_start: string
  period_label: string
  supplier_revenue: number
  comparable_market_revenue: number
  estimated_market_share_pct: number
}

export interface RevenueTrendResponse {
  supplier_code: string
  period_type: string
  found: boolean
  message?: string
  points: RevenueTrendPoint[]
}

export interface ProductResult {
  sku: string
  product_name: string
  category: string
  total_revenue: number
  total_units: number
  total_orders: number
}

export interface TopProductsResponse {
  supplier_code: string
  found: boolean
  sort_by: string
  limit: number
  message?: string
  products: ProductResult[]
}
