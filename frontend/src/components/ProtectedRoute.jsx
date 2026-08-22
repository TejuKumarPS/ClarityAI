import { useEffect } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useRouter } from '../router/Router'

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const { navigate } = useRouter()

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate('/login')
    }
  }, [loading, isAuthenticated, navigate])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-300">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
          <p className="text-sm font-medium text-slate-400">Loading ClarityAI session...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return children
}
