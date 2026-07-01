const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

let _demoUserId: string | null = null

export function setDemoUser(userId: string): void {
  _demoUserId = userId
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
  if (_demoUserId) {
    headers['X-Demo-User-Id'] = _demoUserId
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
