import { useState, useRef } from 'react'
import { apiClient } from '../api/client'
import { useRouter } from '../router/Router'

const MIN_TRANSCRIPT_LENGTH = 10
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 // 10MB
const ALLOWED_EXTENSIONS = ['txt', 'pdf']

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function JobCreateForm({ onJobCreated }) {
  const [activeTab, setActiveTab] = useState('text') // 'text' | 'file'
  const [content, setContent] = useState('')
  const [file, setFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fileInputRef = useRef(null)
  const { navigate } = useRouter()

  const trimmedLength = content.trim().length
  const isTextValid = trimmedLength >= MIN_TRANSCRIPT_LENGTH
  const isFileValid = !!file
  const canSubmit = activeTab === 'text' ? isTextValid : isFileValid

  const handleTabChange = (tab) => {
    if (tab === activeTab) return
    setActiveTab(tab)
    setError(null)
    if (tab === 'text') {
      setFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } else {
      setContent('')
    }
  }

  const validateAndSetFile = (selectedFile) => {
    if (!selectedFile) return

    const ext = selectedFile.name.split('.').pop().toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError('Please select a valid .txt or .pdf file.')
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      setError('File exceeds 10MB limit.')
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    setError(null)
    setFile(selectedFile)
  }

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0]
    validateAndSetFile(selected)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragEnter = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const droppedFile = e.dataTransfer.files?.[0]
    if (droppedFile) {
      validateAndSetFile(droppedFile)
    }
  }

  const handleRemoveFile = (e) => {
    e.stopPropagation()
    setFile(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (activeTab === 'text') {
      if (!isTextValid) {
        setError(`Transcript must be at least ${MIN_TRANSCRIPT_LENGTH} characters.`)
        return
      }
    } else {
      if (!isFileValid) {
        setError('Please select a .txt or .pdf file to upload.')
        return
      }
    }

    setLoading(true)
    setError(null)

    try {
      let job
      if (activeTab === 'text') {
        job = await apiClient.createTextJob(content.trim())
        setContent('')
      } else {
        job = await apiClient.createFileJob(file)
        setFile(null)
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }

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
      {/* Header with Title and Mode Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white tracking-tight">Create New Processing Job</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Submit meeting transcripts for multi-stage structured intelligence extraction.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="inline-flex p-1 bg-slate-950/80 rounded-xl border border-slate-800 shrink-0 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => handleTabChange('text')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'text'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Paste Text
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('file')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'file'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Upload File
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {/* Error Alert */}
        {error && (
          <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs flex items-start gap-2.5">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-1.5 shrink-0"></span>
            <span>{error}</span>
          </div>
        )}

        {/* Mode 1: Text Paste */}
        {activeTab === 'text' && (
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
        )}

        {/* Mode 2: File Upload */}
        {activeTab === 'file' && (
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Transcript Document (.txt or .pdf)
            </label>

            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.pdf"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload-input"
              disabled={loading}
            />

            {!file ? (
              <div
                onDragOver={handleDragOver}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`w-full rounded-xl border-2 border-dashed transition-all p-8 flex flex-col items-center justify-center gap-3 cursor-pointer select-none min-h-[140px] ${
                  isDragging
                    ? 'border-blue-500 bg-blue-950/20'
                    : 'border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-950/80'
                }`}
              >
                <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div className="text-center space-y-1">
                  <p className="text-xs font-medium text-slate-300">
                    <span className="text-blue-400 hover:underline">Click to browse</span> or drag and drop your file here
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Supports <span className="font-mono text-slate-400">.txt</span> and <span className="font-mono text-slate-400">.pdf</span> (Max 10MB)
                  </p>
                </div>
              </div>
            ) : (
              <div className="w-full rounded-xl bg-slate-950/80 border border-slate-800 p-4 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-blue-950/60 border border-blue-800/60 flex items-center justify-center text-blue-400 shrink-0">
                    {file.name.endsWith('.pdf') ? (
                      <span className="font-bold text-[10px] uppercase font-mono">PDF</span>
                    ) : (
                      <span className="font-bold text-[10px] uppercase font-mono">TXT</span>
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-200 truncate">{file.name}</p>
                    <p className="text-[11px] text-slate-500 font-mono">
                      {formatFileSize(file.size)} • <span className="uppercase text-slate-400">{file.name.endsWith('.pdf') ? 'pdf_file' : 'txt_file'}</span>
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleRemoveFile}
                  disabled={loading}
                  title="Remove file"
                  className="px-2.5 py-1 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-950/40 border border-transparent hover:border-rose-800/60 transition-all cursor-pointer"
                >
                  ✕ Remove
                </button>
              </div>
            )}
          </div>
        )}

        {/* Action Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          {activeTab === 'text' ? (
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>
                Characters: <strong className="font-mono text-slate-300">{trimmedLength}</strong>
              </span>
              <span>•</span>
              <span className={trimmedLength > 0 && !isTextValid ? 'text-amber-400' : 'text-slate-500'}>
                Min required: <span className="font-mono">{MIN_TRANSCRIPT_LENGTH}</span>
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span>Selected mode:</span>
              <strong className="font-mono text-slate-300">
                {file ? (file.name.endsWith('.pdf') ? 'pdf_file' : 'txt_file') : 'No file chosen'}
              </strong>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !canSubmit}
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
