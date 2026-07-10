export interface DashboardUser {
  user_id: string
  display_name: string
  supplier_id: string
}

export interface KpiCardData {
  key: string
  label: string
  value: number
  unit: string | null
}

export interface DashboardArtifact {
  source_tool: string
  result_type: string
  title: string
  description?: string
  columns: Array<Record<string, unknown>>
  rows: Array<Record<string, unknown>>
  recommended_visualizations?: Array<Record<string, unknown>>
  data_quality?: Record<string, unknown>
  primary_metric?: string
  dimension?: string
  result_intent?: string
}

export interface DashboardResponse {
  user: DashboardUser
  cards: KpiCardData[]
  artifacts: DashboardArtifact[]
}

// --- Shared types ---

export type Metric = 'net_sales' | 'gross_sales' | 'units' | 'orders' | 'discounts'
export type Grain = 'week' | 'month'

// --- Widget endpoint response types ---

export interface SummaryResponse {
  date_from: string | null
  date_to: string | null
  gross_sales: number
  net_sales: number
  discounts: number
  units: number
  orders: number
}

export interface TimeseriesRow {
  period: string
  product_id: string
  product_name: string
  category: string
  value: number
}

export interface ProductTimeseriesResponse {
  date_from: string | null
  date_to: string | null
  grain: Grain
  metric: Metric
  limit_products: number
  rows: TimeseriesRow[]
}

export interface TopProductsRow {
  rank: number
  product_id: string
  product_name: string
  category: string
  net_sales: number
  gross_sales: number
  units: number
  orders: number
  discounts: number
}

export interface TopProductsResponse {
  date_from: string | null
  date_to: string | null
  sort_by: Metric
  limit: number
  rows: TopProductsRow[]
}

export interface ProductSelectorItem {
  product_id: string
  product_name: string
  category: string
  net_sales: number
  units: number
}

export interface ProductsResponse {
  date_from: string | null
  date_to: string | null
  products: ProductSelectorItem[]
}
