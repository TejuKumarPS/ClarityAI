import { useState, useEffect } from 'react'

export default function App() {
  const [healthData, setHealthData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [latency, setLatency] = useState(null)
  const [activeEndpoint, setActiveEndpoint] = useState('/health')

  const checkHealth = async (endpoint = activeEndpoint) => {
    setLoading(true)
    setError(null)
    const startTime = performance.now()
    try {
      const response = await fetch(endpoint)
      const duration = Math.round(performance.now() - startTime)
      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status} ${response.statusText}`)
      }
      const data = await response.json()
      setHealthData(data)
      setLatency(duration)
    } catch (err) {
      setError(err.message || 'Failed to connect to backend')
      setHealthData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    checkHealth(activeEndpoint)
  }, [activeEndpoint])

  return (
    <div className="min-h-screen flex flex-col justify-between bg-slate-950 text-slate-100 p-6 md:p-12">
      <div className="max-w-4xl mx-auto w-full">
        {/* Header */}
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-8 border-b border-slate-800 gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-xl text-white shadow-lg shadow-blue-500/20">
                C
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-white">ClarityAI</h1>
            </div>
            <p className="text-sm text-slate-400 mt-1">Meeting Intelligence Platform</p>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-300 border border-blue-800/60">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
            Milestone 0: Project Foundation
          </div>
        </header>

        {/* Main Content */}
        <main className="mt-10 space-y-6">
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 md:p-8 shadow-xl">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
              <div>
                <h2 className="text-xl font-semibold text-white">Backend Connection Status</h2>
                <p className="text-sm text-slate-400 mt-0.5">
                  Verifying direct communication between React and FastAPI
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const nextEndpoint = activeEndpoint === '/health' ? '/api/v1/health' : '/health'
                    setActiveEndpoint(nextEndpoint)
                  }}
                  className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
                >
                  Endpoint: <span className="font-mono text-blue-400">{activeEndpoint}</span>
                </button>

                <button
                  type="button"
                  onClick={() => checkHealth(activeEndpoint)}
                  disabled={loading}
                  className="text-xs font-medium px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-all disabled:opacity-50"
                >
                  {loading ? 'Checking...' : 'Re-check'}
                </button>
              </div>
            </div>

            {/* Health Result */}
            <div className="mt-6">
              {loading && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 text-slate-300">
                  <div className="w-4 h-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin"></div>
                  <span className="text-sm font-medium">Checking backend status...</span>
                </div>
              )}

              {!loading && error && (
                <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 flex items-start gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-rose-500 mt-1.5 shrink-0"></div>
                  <div>
                    <div className="text-sm font-semibold">Backend Unreachable</div>
                    <div className="text-xs text-rose-400 mt-1 font-mono">{error}</div>
                  </div>
                </div>
              )}

              {!loading && healthData && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
                    <div className="flex-1 flex items-center justify-between flex-wrap gap-2">
                      <span className="text-sm font-semibold">Backend Connected (Healthy)</span>
                      {latency !== null && (
                        <span className="text-xs font-mono text-emerald-400 bg-emerald-900/40 px-2 py-0.5 rounded border border-emerald-800/40">
                          {latency}ms latency
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="bg-slate-950/80 rounded-xl p-4 border border-slate-800/80 font-mono text-xs text-slate-300">
                    <div className="text-slate-500 mb-2 font-sans font-medium uppercase tracking-wider text-[10px]">
                      Response Payload
                    </div>
                    <pre className="overflow-x-auto text-emerald-400 leading-relaxed">
                      {JSON.stringify(healthData, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Footer */}
      <footer className="max-w-4xl mx-auto w-full pt-8 text-center text-xs text-slate-500 border-t border-slate-800/60 mt-12">
        ClarityAI • Layered Monolith Architecture • Milestone 0 Foundation Complete
      </footer>
    </div>
  )
}
