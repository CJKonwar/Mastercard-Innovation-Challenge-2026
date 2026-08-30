import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchCurrentJob, fetchJob, startRun, stopJob, type JobState } from './api'

export function useJob(vector: string, onDone?: () => void) {
  const [job, setJob] = useState<JobState | null>(null)
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const onDoneRef = useRef(onDone)
  onDoneRef.current = onDone

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = null
  }

  const poll = useCallback((jobId: string) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const j = await fetchJob(jobId)
        setJob(j)
        if (j.status !== 'running') {
          stopPolling()
          onDoneRef.current?.()
        }
      } catch {
        stopPolling()
      }
    }, 1500)
  }, [])

  useEffect(() => {
    fetchCurrentJob(vector).then((j) => {
      if (j) {
        setJob(j)
        if (j.status === 'running') poll(j.id)
      }
    }).catch(() => {})
    return stopPolling
  }, [vector, poll])

  const run = async (params: Record<string, unknown>) => {
    setError(null)
    setStarting(true)
    try {
      const j = await startRun(vector, params)
      setJob(j)
      poll(j.id)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setStarting(false)
    }
  }

  const stop = async () => {
    if (!job) return
    setError(null)
    setStopping(true)
    try {
      const j = await stopJob(job.id)
      setJob(j)
      if (j.status === 'running') poll(j.id)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setStopping(false)
    }
  }

  return { job, run, stop, starting, stopping, error, isRunning: job?.status === 'running' }
}
