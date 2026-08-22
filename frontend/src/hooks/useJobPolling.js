import { useState, useEffect, useRef, useCallback } from 'react'
import { apiClient } from '../api/client'

export function useJobPolling(jobId) {
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isPolling, setIsPolling] = useState(false)

  const isMountedRef = useRef(true)
  const inFlightRef = useRef(false)
  const timerRef = useRef(null)

  const fetchJob = useCallback(async (isInitial = false) => {
    if (!jobId || inFlightRef.current) return
    inFlightRef.current = true

    if (isInitial) {
      setLoading(true)
      setError(null)
    }

    try {
      const data = await apiClient.getJob(jobId)
      if (!isMountedRef.current) return

      setJob(data)
      setError(null)

      const isTerminal = data.status === 'complete' || data.status === 'failed'
      if (isTerminal) {
        setIsPolling(false)
        if (timerRef.current) {
          clearTimeout(timerRef.current)
          timerRef.current = null
        }
      } else {
        setIsPolling(true)
        if (timerRef.current) {
          clearTimeout(timerRef.current)
        }
        timerRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            fetchJob(false)
          }
        }, 2000)
      }
    } catch (err) {
      if (!isMountedRef.current) return
      setError(err.message || 'Failed to load job details')
      setIsPolling(false)
    } finally {
      inFlightRef.current = false
      if (isMountedRef.current && isInitial) {
        setLoading(false)
      }
    }
  }, [jobId])

  useEffect(() => {
    isMountedRef.current = true
    fetchJob(true)

    return () => {
      isMountedRef.current = false
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [fetchJob])

  const refresh = useCallback(() => {
    fetchJob(true)
  }, [fetchJob])

  return {
    job,
    loading,
    error,
    isPolling,
    refresh,
  }
}
