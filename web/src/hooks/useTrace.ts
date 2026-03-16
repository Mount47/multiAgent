import { useEffect, useState } from 'react'
import { fetchTrace } from '../api/client'
import type { TraceResponse } from '../types/api'

export function useTrace(taskId: string | null) {
  const [trace, setTrace] = useState<TraceResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!taskId) { setTrace(null); return }
    setLoading(true)
    fetchTrace(taskId)
      .then(setTrace)
      .catch(() => setTrace(null))
      .finally(() => setLoading(false))
  }, [taskId])

  return { trace, loading }
}
