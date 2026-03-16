import { useEffect, useState, useRef, useCallback } from 'react'
import { fetchMetrics } from '../api/client'
import type { MetricsResponse } from '../types/api'

export function useMetrics(enabled: boolean, intervalMs = 10000) {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const timerRef = useRef<ReturnType<typeof setInterval>>()

  const load = useCallback(() => {
    fetchMetrics()
      .then(setMetrics)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!enabled) return
    load()
    timerRef.current = setInterval(load, intervalMs)
    return () => clearInterval(timerRef.current)
  }, [enabled, intervalMs, load])

  return { metrics, loading }
}
