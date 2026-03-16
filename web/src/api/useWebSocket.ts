import { useEffect, useRef, useState, useCallback } from 'react'
import { API } from './endpoints'
import type { TaskEvent, TaskStatus } from '../types/api'
import type { WsMessage } from '../types/websocket'

export interface TaskStreamState {
  events: TaskEvent[]
  activeState: string | null
  visitedStates: Set<string>
  status: TaskStatus | 'idle'
  error: string | null
  isConnected: boolean
}

export function useTaskWebSocket(taskId: string | null): TaskStreamState {
  const [events, setEvents] = useState<TaskEvent[]>([])
  const [activeState, setActiveState] = useState<string | null>(null)
  const [visitedStates, setVisitedStates] = useState<Set<string>>(new Set())
  const [status, setStatus] = useState<TaskStatus | 'idle'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const reset = useCallback(() => {
    setEvents([])
    setActiveState(null)
    setVisitedStates(new Set())
    setStatus('idle')
    setError(null)
    setIsConnected(false)
  }, [])

  useEffect(() => {
    if (!taskId) {
      reset()
      return
    }

    const url = API.TASK_WS(taskId)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setIsConnected(true)

    ws.onmessage = (ev) => {
      const msg: WsMessage = JSON.parse(ev.data)

      if (msg.type === 'event') {
        setEvents((prev) => [...prev, {
          timestamp: msg.timestamp,
          source: msg.source,
          content: msg.content,
        }])
      } else if (msg.type === 'state_change') {
        setActiveState((prev) => {
          if (prev) setVisitedStates((vs) => new Set([...vs, prev]))
          return msg.state
        })
      } else if (msg.type === 'status') {
        setStatus(msg.status as TaskStatus)
        if (msg.status === 'completed') {
          setActiveState((prev) => {
            if (prev) setVisitedStates((vs) => new Set([...vs, prev, 'approved']))
            return 'approved'
          })
        }
        if (msg.error) setError(msg.error)
      }
    }

    ws.onerror = () => setError('WebSocket disconnected')
    ws.onclose = () => setIsConnected(false)

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [taskId, reset])

  return { events, activeState, visitedStates, status, error, isConnected }
}
