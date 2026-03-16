import { useEffect, useState, useCallback } from 'react'
import { fetchTasks } from '../api/client'
import type { TaskSummary } from '../types/api'

export function useTasks() {
  const [tasks, setTasks] = useState<TaskSummary[]>([])
  const [loading, setLoading] = useState(true)

  const refetch = useCallback(() => {
    fetchTasks()
      .then(setTasks)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { refetch() }, [refetch])

  return { tasks, loading, refetch }
}
