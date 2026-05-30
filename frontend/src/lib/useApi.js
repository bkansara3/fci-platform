import { useState, useEffect, useCallback, useRef } from 'react'

export function useApi(fn, deps = []) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const fnRef = useRef(fn)
  fnRef.current = fn

  const execute = useCallback(async () => {
    setLoading(true); setError(null)
    try   { setData(await fnRef.current()) }
    catch (e) { setError(e.message) }
    finally   { setLoading(false) }
  }, deps) // eslint-disable-line

  useEffect(() => { execute() }, [execute])
  return { data, loading, error, refetch: execute }
}
