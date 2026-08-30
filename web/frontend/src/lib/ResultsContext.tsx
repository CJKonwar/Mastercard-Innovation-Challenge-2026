import { createContext, useContext, type ReactNode } from 'react'
import { useResults } from './useResults'
import type { LiveResults } from './api'

interface Ctx {
  data: LiveResults | null
  loading: boolean
  error: string | null
  backendUp: boolean | null
  refetch: () => Promise<void>
}

const ResultsCtx = createContext<Ctx | null>(null)

export function ResultsProvider({ children }: { children: ReactNode }) {
  const value = useResults()
  return <ResultsCtx.Provider value={value}>{children}</ResultsCtx.Provider>
}

export function useResultsContext(): Ctx {
  const ctx = useContext(ResultsCtx)
  if (!ctx) throw new Error('useResultsContext must be used inside ResultsProvider')
  return ctx
}
