const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const TOKEN_STORAGE_KEY = 'retail_bi_access_token'
const LEGACY_TOKEN_STORAGE_KEY = 'agent_token'

export const AUTH_UNAUTHORIZED_EVENT = 'auth:unauthorized'

export function setAuthToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }

    // The old frontend used this key for manually generated dev tokens.
    localStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY)
  } catch {
    // localStorage unavailable (SSR/tests) — ignore.
  }
}

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // Fall through to status text.
  }

  return res.statusText || `Request failed with status ${res.status}`
}

function notifyUnauthorized(): void {
  setAuthToken(null)

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT))
  }
}

export async function apiFetch<T>(
  path: string,
  init?: Omit<RequestInit, 'headers'>,
): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getAuthToken()

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  if (init?.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!res.ok) {
    const message = await errorMessage(res)

    // A failed login is just bad credentials. A 401 from any protected API
    // means the current session is no longer usable (usually expiry).
    if (res.status === 401 && path !== '/auth/login') {
      notifyUnauthorized()
    }

    throw new ApiError(res.status, message)
  }

  return res.json() as Promise<T>
}
