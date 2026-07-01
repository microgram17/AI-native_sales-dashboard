import { apiFetch } from './client'
import type {
  DemoUsersResponse,
  SuppliersResponse,
  SupplierSummary,
  RevenueTrendResponse,
  TopProductsResponse,
} from '../types/dashboard'

export const dashboardApi = {
  listDemoUsers: () =>
    apiFetch<DemoUsersResponse>('/api/demo/users'),

  listSuppliers: () =>
    apiFetch<SuppliersResponse>('/api/dashboard/suppliers'),

  getSupplierSummary: (supplierCode: string) =>
    apiFetch<SupplierSummary>(
      `/api/dashboard/summary/${encodeURIComponent(supplierCode)}`,
    ),

  getRevenueTrend: (
    supplierCode: string,
    periodType: 'month' | 'week' = 'month',
  ) =>
    apiFetch<RevenueTrendResponse>(
      `/api/dashboard/trend/${encodeURIComponent(supplierCode)}?period_type=${periodType}`,
    ),

  getTopProducts: (
    supplierCode: string,
    limit = 5,
    sortBy: 'revenue' | 'units' | 'orders' = 'revenue',
  ) =>
    apiFetch<TopProductsResponse>(
      `/api/dashboard/top-products/${encodeURIComponent(supplierCode)}?limit=${limit}&sort_by=${sortBy}`,
    ),
}
