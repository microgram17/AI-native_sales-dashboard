import { apiFetch } from './client'
import type {
  Grain,
  Metric,
  PerformanceTimeseriesResponse,
  ProductTableResponse,
  ProductSortDirection,
  ProductsResponse,
  ProductTimeseriesResponse,
  SalesTimeseriesResponse,
  StoreBreakdownResponse,
  StoreGroupBy,
  SummaryResponse,
  TopProductsResponse,
} from '../types/dashboard'

function buildUrl(path: string, params: object): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  }
  const qs = searchParams.toString()
  return qs ? `${path}?${qs}` : path
}

export interface SummaryParams {
  date_from?: string
  date_to?: string
}

export interface ProductTimeseriesParams {
  date_from?: string
  date_to?: string
  grain?: Grain
  metric?: Metric
  product_ids?: string
  limit_products?: number
}

export interface SalesTimeseriesParams extends DateRangeParams {
  grain?: Grain
  metric?: Metric
}

export interface TopProductsParams {
  date_from?: string
  date_to?: string
  sort_by?: Metric
  limit?: number
}

export interface ProductTableParams extends DateRangeParams {
  sort_by?: Metric
  sort_direction?: ProductSortDirection
  offset?: number
  limit?: number
}

export interface DateRangeParams {
  date_from?: string
  date_to?: string
}

export interface StoreBreakdownParams extends DateRangeParams {
  metric?: Metric
  group_by?: StoreGroupBy
}

export interface PerformanceTimeseriesParams extends StoreBreakdownParams {
  grain?: Grain
  group_ids?: string
  limit_groups?: number
}

export const dashboardApi = {
  getSummary: (params: SummaryParams) =>
    apiFetch<SummaryResponse>(buildUrl('/dashboard/summary', params)),

  getProductTimeseries: (params: ProductTimeseriesParams) =>
    apiFetch<ProductTimeseriesResponse>(
      buildUrl('/dashboard/product-timeseries', params),
    ),

  getSalesTimeseries: (params: SalesTimeseriesParams) =>
    apiFetch<SalesTimeseriesResponse>(
      buildUrl('/dashboard/sales-timeseries', params),
    ),

  getTopProducts: (params: TopProductsParams) =>
    apiFetch<TopProductsResponse>(
      buildUrl('/dashboard/top-products', params),
    ),

  getProductTable: (params: ProductTableParams) =>
    apiFetch<ProductTableResponse>(
      buildUrl('/dashboard/product-table', params),
    ),

  getProducts: (params: DateRangeParams) =>
    apiFetch<ProductsResponse>(buildUrl('/dashboard/products', params)),

  getStoreBreakdown: (params: StoreBreakdownParams) =>
    apiFetch<StoreBreakdownResponse>(
      buildUrl('/dashboard/store-breakdown', params),
    ),


  getPerformanceTimeseries: (params: PerformanceTimeseriesParams) =>
    apiFetch<PerformanceTimeseriesResponse>(
      buildUrl('/dashboard/performance-timeseries', params),
    ),
}
