import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'
import { useRouter } from '../router/Router'
import { JobCreateForm } from '../components/JobCreateForm'
import { JobStatusBadge } from '../components/job/JobStatusBadge'

export function Jobs() {
  const [jobs, setJobs] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const { navigate } = useRouter()

  const loadJobs = useCallback(async (targetPage = page) => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiClient.listJobs(targetPage, pageSize)
      setJobs(data.items || [])
      setPage(data.page || 1)
      setTotal(data.total || 0)
      setPages(data.pages || 0)
    } catch (err) {
      setError(err.message || 'Failed to retrieve job history')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  useEffect(() => {
    loadJobs(page)
  }, [page, loadJobs])

  const handleJobCreated = (newJob) => {
    navigate(`/jobs/${newJob.id}`)
  }

  const formatDate = (isoString) => {
    if (!isoString) return '—'
    try {
      return new Date(isoString).toLocaleString()
    } catch {
      return isoString
    }
  }

  const formatDuration = (ms) => {
    if (ms === null || ms === undefined) return '—'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Transcript Intelligence Dashboard</h1>
        <p className="text-xs text-slate-400 mt-1">
          Submit transcripts for AI analysis and monitor your asynchronous processing jobs
        </p>
      </div>

      {/* Job Creation Form */}
      <JobCreateForm onJobCreated={handleJobCreated} />

      {/* Job History Section */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 md:p-8 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">Job History</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {jobs.length} of {total} total processing jobs
            </p>
          </div>

          <button
            type="button"
            onClick={() => loadJobs(page)}
            disabled={loading}
            className="self-start sm:self-auto px-3.5 py-1.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh List'}
          </button>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {loading && jobs.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
            <div className="w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
            <span className="text-xs">Loading job history...</span>
          </div>
        ) : jobs.length === 0 ? (
          <div className="py-12 text-center text-slate-400 bg-slate-950/40 rounded-xl border border-slate-800/60 space-y-2">
            <p className="text-sm font-medium text-slate-300">No processing jobs yet</p>
            <p className="text-xs text-slate-500">
              Submit your first transcript in the form above to extract structured meeting intelligence.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Desktop Table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                    <th className="pb-3 font-semibold">Job ID</th>
                    <th className="pb-3 font-semibold">Input Type</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold">Created At</th>
                    <th className="pb-3 font-semibold">Duration</th>
                    <th className="pb-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 font-mono text-slate-300">
                        <span title={job.id}>{job.id.substring(0, 8)}...</span>
                      </td>
                      <td className="py-3.5 text-slate-400">
                        <span className="font-mono text-[11px] bg-slate-800 px-2 py-0.5 rounded border border-slate-700/60">
                          {job.input_type}
                        </span>
                      </td>
                      <td className="py-3.5">
                        <JobStatusBadge status={job.status} />
                      </td>
                      <td className="py-3.5 text-slate-300">
                        {formatDate(job.created_at)}
                      </td>
                      <td className="py-3.5 font-mono text-slate-400">
                        {formatDuration(job.processing_duration_ms)}
                      </td>
                      <td className="py-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => navigate(`/jobs/${job.id}`)}
                          className="px-3 py-1 rounded-lg text-xs font-medium text-blue-400 hover:text-blue-300 hover:bg-blue-950/40 border border-blue-900/60 transition-colors cursor-pointer"
                        >
                          View Results →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Card List */}
            <div className="md:hidden space-y-3">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2.5 cursor-pointer hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-slate-300 font-semibold">
                      {job.id.substring(0, 8)}...
                    </span>
                    <JobStatusBadge status={job.status} />
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>{formatDate(job.created_at)}</span>
                    <span className="font-mono">{formatDuration(job.processing_duration_ms)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination Controls */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800/80 text-xs text-slate-400">
              <div>
                Page <strong className="text-slate-200">{page}</strong> of <strong className="text-slate-200">{pages || 1}</strong>
                <span className="text-slate-600 mx-2">•</span>
                Total <strong className="text-slate-200">{total}</strong> jobs
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  disabled={page <= 1 || loading}
                  className="px-3 py-1.5 rounded-lg font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  ← Previous
                </button>
                <button
                  type="button"
                  onClick={() => setPage((prev) => (pages && prev < pages ? prev + 1 : prev))}
                  disabled={page >= pages || pages === 0 || loading}
                  className="px-3 py-1.5 rounded-lg font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                >
                  Next →
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
