export function JobMetadata({ job }) {
  if (!job) return null

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
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 shadow-xl space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
        Operational Metadata
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 text-xs">
        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">Created At</span>
          <span className="font-mono text-slate-200 mt-1 block truncate" title={job.created_at}>
            {formatDate(job.created_at)}
          </span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">Completed At</span>
          <span className="font-mono text-slate-200 mt-1 block truncate" title={job.completed_at}>
            {formatDate(job.completed_at)}
          </span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">Processing Duration</span>
          <span className="font-mono text-emerald-400 mt-1 block font-medium">
            {formatDuration(job.processing_duration_ms)}
          </span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">Retry Count</span>
          <span className="font-mono text-slate-200 mt-1 block">
            {job.retry_count || 0}
          </span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">LLM Provider</span>
          <span className="font-mono text-blue-400 mt-1 block font-medium">
            {job.llm_provider || '—'}
          </span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">LLM Model</span>
          <span className="font-mono text-indigo-300 mt-1 block font-medium">
            {job.llm_model || '—'}
          </span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">Prompt / Output Tokens</span>
          <span className="font-mono text-slate-300 mt-1 block">
            {job.llm_input_tokens ?? '—'} / {job.llm_output_tokens ?? '—'}
          </span>
        </div>

        <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
          <span className="text-slate-500 block">Total Tokens</span>
          <span className="font-mono text-purple-400 mt-1 block font-medium">
            {job.llm_total_tokens ?? '—'}
          </span>
        </div>
      </div>
    </div>
  )
}
