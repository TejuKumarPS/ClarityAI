import { useAuth } from '../auth/AuthContext'
import { useRouter } from '../router/Router'

export function AppLayout({ children }) {
  const { user, logout } = useAuth()
  const { currentPath, navigate } = useRouter()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-950 text-slate-100 selection:bg-blue-600 selection:text-white">
      <div className="w-full">
        {/* Navigation Bar */}
        <header className="border-b border-slate-800/80 bg-slate-900/40 backdrop-blur sticky top-0 z-20">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
            <div className="flex items-center gap-6">
              <button
                type="button"
                onClick={() => navigate('/jobs')}
                className="flex items-center gap-3 text-left focus:outline-none group cursor-pointer"
              >
                <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-lg text-white shadow-lg shadow-blue-500/20 group-hover:bg-blue-500 transition-colors">
                  C
                </div>
                <div>
                  <span className="font-bold text-lg text-white tracking-tight block leading-tight">
                    ClarityAI
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block">
                    Intelligence Platform
                  </span>
                </div>
              </button>

              <nav className="hidden sm:flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => navigate('/jobs')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                    currentPath.startsWith('/jobs')
                      ? 'bg-slate-800 text-white border border-slate-700'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  Jobs Dashboard
                </button>
              </nav>
            </div>

            {/* User Profile & Logout */}
            <div className="flex items-center gap-3">
              {user && (
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-medium text-slate-200 truncate max-w-[200px]" title={user.email}>
                    {user.email}
                  </span>
                  <span className="text-[10px] text-emerald-400 font-mono">Authenticated</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleLogout}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-slate-800/80 hover:bg-slate-700 hover:text-white border border-slate-700 transition-all cursor-pointer"
              >
                Log Out
              </button>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-10">
          {children}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 bg-slate-950/60 py-6 text-center text-xs text-slate-500 mt-12">
        <div className="max-w-6xl mx-auto px-4">
          ClarityAI • Intelligent Document & Meeting Intelligence
        </div>
      </footer>
    </div>
  )
}
