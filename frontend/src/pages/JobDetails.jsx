import { useRouter } from '../router/Router'
import { useJobPolling } from '../hooks/useJobPolling'
import { JobStatusBadge } from '../components/job/JobStatusBadge'
import { AIAnalysisCard } from '../components/job/AIAnalysisCard'
import { JobMetadata } from '../components/job/JobMetadata'

export function JobDetails({ jobId }) {
  const { navigate } = useRouter()
  const { job, loading, error, isPolling, refresh } = useJobPolling(jobId)

  const formatDate = (isoString) => {
    if (!isoString) return '—'
    try {
      return new Date(isoString).toLocaleString()
    } catch {
      return isoString
    }
  }

  const getFriendlyErrorMessage = (errorCode, errorPayload) => {
    if (errorPayload && errorPayload.message) {
      return errorPayload.message
    }
    switch (errorCode) {
      case 'LLM_CONFIGURATION_ERROR':
        return 'LLM service is improperly configured. Please check server configuration.'
      case 'LLM_INPUT_TOO_LARGE':
        return 'Transcript input exceeds maximum allowed character limit.'
      case 'LLM_RESPONSE_INVALID':
        return 'LLM provider returned an invalid or unparseable structured response.'
      case 'LLM_PROVIDER_ERROR':
        return 'LLM provider temporarily unavailable or exceeded retry limits.'
      default:
        return 'An error occurred during transcript processing.'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header & Back Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate('/jobs')}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Back to Jobs Dashboard"
          >
            ←
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-white tracking-tight">Job Inspection</h1>
              {job && <JobStatusBadge status={job.status} />}
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5">
              ID: {jobId}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isPolling && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-950/80 text-blue-300 border border-blue-800/60">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
              Live Polling (2s)
            </span>
          )}

          <button
            type="button"
            onClick={refresh}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && !job && (
        <div className="py-16 flex flex-col items-center justify-center gap-4 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
          <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
          <span className="text-sm font-medium">Fetching job details...</span>
        </div>
      )}

      {/* Error / 404 State */}
      {error && !job && (
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-rose-300 space-y-3">
          <div className="flex items-center gap-2 text-base font-semibold">
            <span>Job Not Found or Access Denied</span>
          </div>
          <p className="text-xs text-rose-400 leading-relaxed">{error}</p>
          <button
            type="button"
            onClick={() => navigate('/jobs')}
            className="px-4 py-2 rounded-xl text-xs font-medium bg-rose-900 hover:bg-rose-800 text-white transition-colors cursor-pointer mt-2"
          >
            Return to Dashboard
          </button>
        </div>
      )}

      {/* Processing State Banner */}
      {job && (job.status === 'pending' || job.status === 'processing') && (
        <div className="rounded-2xl bg-blue-950/30 border border-blue-800/50 p-6 md:p-8 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-full border-2 border-blue-400 border-t-transparent animate-spin"></div>
            <div>
              <h3 className="text-sm font-semibold text-blue-200">
                {job.status === 'pending'
                  ? 'Job is queued in Celery'
                  : 'Multi-stage processing pipeline in progress'}
              </h3>
              <p className="text-xs text-blue-400/80 mt-0.5">
                Executing document intelligence stages (Normalize → Analyze → Chunk → Retrieve → AI Analysis)
              </p>
            </div>
          </div>

          <div className="text-xs font-mono text-slate-400 bg-slate-950/60 p-3 rounded-xl border border-blue-900/30">
            Created: {formatDate(job.created_at)} • Auto-refreshing every 2s
          </div>
        </div>
      )}

      {/* Failed State Banner */}
      {job && job.status === 'failed' && (
        <div className="rounded-2xl bg-rose-950/40 border border-rose-800/60 p-6 md:p-8 space-y-3 shadow-xl">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-rose-500"></div>
            <h3 className="text-base font-semibold text-rose-200">Processing Failed</h3>
          </div>
          <p className="text-sm text-rose-300/90 leading-relaxed">
            {getFriendlyErrorMessage(job.error_code, job.result?.error)}
          </p>
          {job.error_code && (
            <div className="text-[11px] font-mono text-rose-400/80 bg-rose-950/80 px-3 py-1.5 rounded-lg border border-rose-900/60 inline-block">
              Code: {job.error_code}
            </div>
          )}
        </div>
      )}

      {/* Completed State: Structured AI Analysis */}
      {job && job.status === 'complete' && job.result?.ai_analysis && (
        <AIAnalysisCard analysis={job.result.ai_analysis} />
      )}

      {/* Operational Metadata */}
      {job && <JobMetadata job={job} />}
    </div>
  )
}
