import { useCallback, useState } from 'react'

export default function useAnalysis(apiFn) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const execute = useCallback(
    async (...args) => {
      setLoading(true)
      setError(null)
      setData(null)
      console.log('[useAnalysis] Executing with args:', args)
      try {
        const result = await apiFn(...args)
        console.log('[useAnalysis] Success:', result)
        setData(result)
        return result
      } catch (err) {
        const message =
          err.response?.data?.detail || err.message || 'Analysis failed'
        console.error('[useAnalysis] Error:', message)
        setError(message)
        return null
      } finally {
        setLoading(false)
      }
    },
    [apiFn],
  )

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setLoading(false)
  }, [])

  return { data, loading, error, execute, reset }
}
