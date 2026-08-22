import { useState } from 'react'
import { apiClient } from '../api/client'
import { useRouter } from '../router/Router'

const MIN_TRANSCRIPT_LENGTH = 10

export function JobCreateForm({ onJobCreated }) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { navigate } = useRouter()

  const trimmedLength = content.trim().length
  const isValidLength = trimmedLength >= MIN_TRANSCRIPT_LENGTH

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!isValidLength) {
      setError(`Transcript must be at least ${MIN_TRANSCRIPT_LENGTH} characters.`)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const job = await apiClient.createTextJob(content.trim())
      setContent('')
      if (onJobCreated) {
        onJobCreated(job)
      } else {
        navigate(`/jobs/${job.id}`)
      }
    } catch (err) {
      setError(err.message || 'Failed to submit transcript for processing')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6 md:p-8 shadow-xl">
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-lg font-bold text-white tracking-tight">Create New Processing Job</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Paste meeting notes or transcript text for multi-stage structured intelligence extraction.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {error && (
          <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs flex items-start gap-2.5">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0"></span>
            <span>{error}</span>
          </div>
        )}

        <div className="space-y-1.5">
          <label htmlFor="transcript-input" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Meeting Transcript Content
          </label>
          <textarea
            id="transcript-input"
            rows={5}
            value={content}
            onChange={(e) => {
              setContent(e.target.value)
              if (error) setError(null)
            }}
            placeholder="Paste raw meeting transcript, notes, or discussion points here..."
            className="w-full rounded-xl bg-slate-950/80 border border-slate-800 px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-sans leading-relaxed resize-y min-h-[120px]"
            disabled={loading}
          />
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>
              Characters: <strong className="font-mono text-slate-300">{trimmedLength}</strong>
            </span>
            <span>•</span>
            <span className={trimmedLength > 0 && !isValidLength ? 'text-amber-400' : 'text-slate-500'}>
              Min required: <span className="font-mono">{MIN_TRANSCRIPT_LENGTH}</span>
            </span>
          </div>

          <button
            type="submit"
            disabled={loading || !isValidLength}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-xs text-white bg-blue-600 hover:bg-blue-500 active:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/10 cursor-pointer"
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
                <span>Creating Job...</span>
              </>
            ) : (
              <span>Start Analysis Job</span>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
