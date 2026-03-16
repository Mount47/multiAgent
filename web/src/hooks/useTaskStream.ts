import { useTaskWebSocket } from '../api/useWebSocket'

export function useTaskStream(taskId: string | null) {
  return useTaskWebSocket(taskId)
}
