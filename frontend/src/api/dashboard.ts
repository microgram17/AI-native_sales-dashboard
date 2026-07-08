import { apiFetch } from './client'
import type {
  DashboardResponse,
  Grain,
  Metric,
  ProductsResponse,
  ProductTimeseriesResponse,
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

export interface TopProductsParams {
  date_from?: string
  date_to?: string
  sort_by?: Metric
  limit?: number
}

export interface DateRangeParams {
  date_from?: string
  date_to?: string
}

export const dashboardApi = {
  getDashboard: () => apiFetch<DashboardResponse>('/dashboard'),

  getSummary: (params: SummaryParams) =>
    apiFetch<SummaryResponse>(buildUrl('/dashboard/summary', params)),

  getProductTimeseries: (params: ProductTimeseriesParams) =>
    apiFetch<ProductTimeseriesResponse>(buildUrl('/dashboard/product-timeseries', params)),

  getTopProducts: (params: TopProductsParams) =>
    apiFetch<TopProductsResponse>(buildUrl('/dashboard/top-products', params)),

  getProducts: (params: DateRangeParams) =>
    apiFetch<ProductsResponse>(buildUrl('/dashboard/products', params)),
}
