import type { ResultsData } from '../data/types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface LiveResults {
  promptInjection: ResultsData['promptInjection'] | null
  tokenReplay: ResultsData['tokenReplay'] | null
  merchantFraud: ResultsData['merchantFraud'] | null
  graphFraud: ResultsData['graphFraud'] | null
  errors: Record<string, string>
}

export interface JobState {
  id: string
  vector: string
  command: string
  status: 'running' | 'done' | 'failed' | 'stopped'
  log: string
  returncode: number | null
  startedAt: number
  finishedAt: number | null
}

export async function fetchResults(): Promise<LiveResults> {
  const res = await fetch(`${API_BASE}/api/results`)
  if (!res.ok) throw new Error(`GET /api/results -> ${res.status}`)
  return res.json()
}

export async function startRun(vector: string, params: Record<string, unknown>): Promise<JobState> {
  const res = await fetch(`${API_BASE}/api/run/${vector}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `POST /api/run/${vector} -> ${res.status}`)
  }
  return res.json()
}

export async function fetchJob(jobId: string): Promise<JobState> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`)
  if (!res.ok) throw new Error(`GET /api/jobs/${jobId} -> ${res.status}`)
  return res.json()
}

export async function stopJob(jobId: string): Promise<JobState> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/stop`, { method: 'POST' })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `POST /api/jobs/${jobId}/stop -> ${res.status}`)
  }
  return res.json()
}

export async function fetchCurrentJob(vector: string): Promise<JobState | null> {
  const res = await fetch(`${API_BASE}/api/vectors/${vector}/current-job`)
  if (!res.ok) throw new Error(`GET current-job -> ${res.status}`)
  const body = await res.json()
  return body ?? null
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(2500) })
    return res.ok
  } catch {
    return false
  }
}
