export type Metric =
  | 'net_sales'
  | 'gross_sales'
  | 'units'
  | 'orders'
  | 'discounts'

export type Grain = 'week' | 'month'
export type StoreGroupBy = 'store' | 'city' | 'channel'
export type ProductSortDirection = 'asc' | 'desc'

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

export interface SalesTimeseriesRow {
  period: string
  value: number
}

export interface SalesTimeseriesResponse {
  date_from: string | null
  date_to: string | null
  grain: Grain
  metric: Metric
  rows: SalesTimeseriesRow[]
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

export interface ProductTableResponse {
  date_from: string | null
  date_to: string | null
  sort_by: Metric
  sort_direction: ProductSortDirection
  offset: number
  limit: number
  total: number
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

export interface StoreBreakdownRow {
  group_id: string
  group_name: string
  value: number
}

export interface StoreBreakdownResponse {
  date_from: string | null
  date_to: string | null
  metric: Metric
  group_by: StoreGroupBy
  rows: StoreBreakdownRow[]
}

export interface PerformanceTimeseriesRow {
  period: string
  group_id: string
  group_name: string
  value: number
}

export interface PerformanceTimeseriesResponse {
  date_from: string | null
  date_to: string | null
  grain: Grain
  metric: Metric
  group_by: StoreGroupBy
  limit_groups: number
  rows: PerformanceTimeseriesRow[]
}

export type PerformanceView = 'ranking' | 'trend'
