const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// Auth token for the backend (Authorization: Bearer). For local dev this can be
// a token from backend/scripts/create_dev_token.py, provided via VITE_AGENT_TOKEN
// at build time or set at runtime with setAuthToken(). The frontend never sends
// or selects supplier identity — that comes from the token on the backend.
const TOKEN_STORAGE_KEY = 'agent_token'

export function setAuthToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token)
    else localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    // localStorage unavailable (SSR/tests) — ignore.
  }
}

export function getAuthToken(): string | null {
  try {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (stored) return stored
  } catch {
    // ignore
  }
  return (import.meta.env.VITE_AGENT_TOKEN as string | undefined) ?? null
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T>(
  path: string,
  init?: Omit<RequestInit, 'headers'>,
): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  if (init?.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, text)
  }
  return res.json() as Promise<T>
}
