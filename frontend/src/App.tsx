import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { DashboardPage } from './features/dashboard/DashboardPage'
import { AuthProvider, useAuth } from './features/auth/AuthContext'
import { LoginPage } from './features/auth/LoginPage'
import { LanguageProvider, useTranslation } from './i18n/LanguageContext'
import { ThemeProvider } from './i18n/ThemeContext'
import './App.css'


const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
    },
  },
})


function AuthenticatedApp() {
  const { status } = useAuth()
  const { t } = useTranslation()

  if (status === 'loading') {
    return (
      <div className="auth-loading">
        {t.loginCheckingSession}
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return <LoginPage />
  }

  return <DashboardPage />
}


function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <AuthenticatedApp />
          </AuthProvider>
        </QueryClientProvider>
      </LanguageProvider>
    </ThemeProvider>
  )
}


export default App
