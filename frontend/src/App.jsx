import { AuthProvider, useAuth } from './auth/AuthContext'
import { RouterProvider, useRouter } from './router/Router'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AppLayout } from './components/AppLayout'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { Jobs } from './pages/Jobs'
import { JobDetails } from './pages/JobDetails'

function AppContent() {
  const { currentPath, navigate } = useRouter()
  const { isAuthenticated, loading } = useAuth()

  // Match /jobs/:jobId
  const jobMatch = currentPath.match(/^\/jobs\/([a-zA-Z0-9-]+)$/)
  const jobId = jobMatch ? jobMatch[1] : null

  if (currentPath === '/' || currentPath === '') {
    if (loading) {
      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-300">
          <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
        </div>
      )
    }
    if (isAuthenticated) {
      return (
        <ProtectedRoute>
          <AppLayout>
            <Jobs />
          </AppLayout>
        </ProtectedRoute>
      )
    }
    return <Login />
  }

  if (currentPath === '/login') {
    return <Login />
  }

  if (currentPath === '/register') {
    return <Register />
  }

  if (currentPath === '/jobs') {
    return (
      <ProtectedRoute>
        <AppLayout>
          <Jobs />
        </AppLayout>
      </ProtectedRoute>
    )
  }

  if (jobId) {
    return (
      <ProtectedRoute>
        <AppLayout>
          <JobDetails jobId={jobId} />
        </AppLayout>
      </ProtectedRoute>
    )
  }

  // 404 Fallback
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-center text-slate-100">
      <div className="max-w-md space-y-4">
        <h1 className="text-4xl font-extrabold text-blue-500 font-mono">404</h1>
        <h2 className="text-xl font-bold text-white">Page Not Found</h2>
        <p className="text-xs text-slate-400">
          The requested page <span className="font-mono text-slate-300">{currentPath}</span> does not exist.
        </p>
        <button
          type="button"
          onClick={() => navigate('/jobs')}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
        >
          Return to Dashboard
        </button>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <RouterProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </RouterProvider>
  )
}
