import { apiFetch } from './client'
import type { DashboardResponse } from '../types/dashboard'

export const dashboardApi = {
  getDashboard: () =>
    apiFetch<DashboardResponse>('/dashboard'),
}
