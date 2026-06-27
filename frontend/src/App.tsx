import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DashboardPage } from './features/dashboard/DashboardPage'
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
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>
  )
}

export default App
