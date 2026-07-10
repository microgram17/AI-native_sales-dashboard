import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { LanguageProvider } from './i18n/LanguageContext'
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

function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <QueryClientProvider client={queryClient}>
          <DashboardPage />
        </QueryClientProvider>
      </LanguageProvider>
    </ThemeProvider>
  )
}

export default App
