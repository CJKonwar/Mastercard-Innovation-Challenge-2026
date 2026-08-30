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
    // Background poll so results also pick up runs started outside the web
    // UI (e.g. `python main.py` in a terminal) - those never fire a job's
    // onDone callback, so without this the page would need a manual reload.
    const id = setInterval(refetch, 15000)
    return () => clearInterval(id)
  }, [refetch])

  return { ...state, refetch }
}
