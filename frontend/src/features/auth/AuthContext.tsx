import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { authApi, type AuthUser } from '../../api/auth'
import {
  AUTH_UNAUTHORIZED_EVENT,
  getAuthToken,
  setAuthToken,
} from '../../api/client'


type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

interface AuthContextValue {
  status: AuthStatus
  user: AuthUser | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)


export class RetailerAdminUiNotImplementedError extends Error {
  constructor() {
    super('Retailer admin supplier selection is not implemented in this MVP.')
    this.name = 'RetailerAdminUiNotImplementedError'
  }
}


export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<AuthUser | null>(null)

  const clearSession = useCallback(() => {
    setAuthToken(null)
    queryClient.clear()
    setUser(null)
    setStatus('unauthenticated')
  }, [queryClient])

  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      if (!getAuthToken()) {
        if (!cancelled) setStatus('unauthenticated')
        return
      }

      try {
        const currentUser = await authApi.me()
        if (cancelled) return

        queryClient.clear()
        setUser(currentUser)
        setStatus('authenticated')
      } catch {
        if (!cancelled) clearSession()
      }
    }

    void restoreSession()

    const onUnauthorized = () => {
      if (!cancelled) clearSession()
    }
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, onUnauthorized)

    return () => {
      cancelled = true
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, onUnauthorized)
    }
  }, [clearSession, queryClient])

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await authApi.login({
        email: email.trim(),
        password,
      })

      // Backend support for retailer-admin supplier selection exists, but the
      // current dashboard has no supplier selector for that account type yet.
      if (response.account_type === 'retailer_admin') {
        clearSession()
        throw new RetailerAdminUiNotImplementedError()
      }

      setAuthToken(response.access_token)

      try {
        const currentUser = await authApi.me()
        queryClient.clear()
        setUser(currentUser)
        setStatus('authenticated')
      } catch (error) {
        clearSession()
        throw error
      }
    },
    [clearSession, queryClient],
  )

  const logout = useCallback(() => {
    clearSession()
  }, [clearSession])

  return (
    <AuthContext.Provider value={{ status, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}


export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
