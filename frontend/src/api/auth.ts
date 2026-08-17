import { apiFetch } from './client'

export type AccountType = 'supplier' | 'retailer_admin'

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  account_type: AccountType
}

export interface AuthUser {
  user_id: string
  email: string | null
  display_name: string | null
  account_type: AccountType
  supplier_id: string
  roles: string[]
}

export const authApi = {
  login: (request: LoginRequest) =>
    apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  me: () => apiFetch<AuthUser>('/auth/me'),
}
