import { useCallback, useEffect, useState } from 'react'
import { checkHealth, fetchResults, type LiveResults } from './api'

interface State {
  data: LiveResults | null
  loading: boolean
  error: string | null
  backendUp: boolean | null
}

export function useResults() {
  const [state, setState] = useState<State>({ data: null, loading: true, error: null, backendUp: null })

  const refetch = useCallback(async () => {
    const up = await checkHealth()
    if (!up) {
      setState((s) => ({ ...s, loading: false, backendUp: false }))
      return
    }
    try {
      const data = await fetchResults()
      setState({ data, loading: false, error: null, backendUp: true })
    } catch (e) {
      setState((s) => ({ ...s, loading: false, error: (e as Error).message, backendUp: true }))
    }
  }, [])

  useEffect(() => {
    refetch()
  }, [refetch])

  return { ...state, refetch }
}
