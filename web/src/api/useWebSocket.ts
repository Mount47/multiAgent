import { useEffect, useRef, useState, useCallback } from 'react'
import { API } from './endpoints'
import type { TaskEvent, TaskStatus } from '../types/api'
import type { WsMessage, WsApprovalRequestMessage } from '../types/websocket'

// HITL: Pending approval state
export interface PendingApproval {
  checkpoint: string
  agent: string
  content: string
}

export interface TaskStreamState {
  events: TaskEvent[]
  activeState: string | null
  visitedStates: Set<string>
  status: TaskStatus | 'idle'
  error: string | null
  isConnected: boolean
  // HITL
  pendingApproval: PendingApproval | null
  sendApprovalResponse: (action: 'approve' | 'revise', feedback?: string) => void
}

export function useTaskWebSocket(taskId: string | null): TaskStreamState {
  const [events, setEvents] = useState<TaskEvent[]>([])
  const [activeState, setActiveState] = useState<string | null>(null)
  const [visitedStates, setVisitedStates] = useState<Set<string>>(new Set())
  const [status, setStatus] = useState<TaskStatus | 'idle'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const reset = useCallback(() => {
    setEvents([])
    setActiveState(null)
    setVisitedStates(new Set())
    setStatus('idle')
    setError(null)
    setIsConnected(false)
    setPendingApproval(null)
  }, [])

  // HITL: Send approval response to backend
  const sendApprovalResponse = useCallback((action: 'approve' | 'revise', feedback?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'approval_response',
        action,
        feedback: feedback || '',
      }))
      setPendingApproval(null)
    }
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
      } else if (msg.type === 'approval_request') {
        // HITL: Show approval dialog
        const approvalMsg = msg as WsApprovalRequestMessage
        setPendingApproval({
          checkpoint: approvalMsg.checkpoint,
          agent: approvalMsg.content.agent,
          content: approvalMsg.content.content,
        })
      }
    }

    ws.onerror = () => setError('WebSocket disconnected')
    ws.onclose = () => setIsConnected(false)

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [taskId, reset])

  return { events, activeState, visitedStates, status, error, isConnected, pendingApproval, sendApprovalResponse }
}
