import type { TaskStatus } from '../../types/api'

const colors: Record<string, string> = {
  queued: 'text-muted border-line',
  running: 'text-accent border-accent',
  completed: 'text-ok border-ok',
  failed: 'text-err border-err',
  idle: 'text-muted border-line',
  waiting_approval: 'text-amber-600 border-amber-500 bg-amber-50',
}

const labels: Record<string, string> = {
  queued: 'queued',
  running: 'running',
  completed: 'completed',
  failed: 'failed',
  idle: 'idle',
  waiting_approval: '等待确认',
}

export function StatusBadge({ status }: { status: TaskStatus | 'idle' }) {
  return (
    <span className={`text-xs font-semibold border rounded-full px-2 py-0.5 ${colors[status] ?? colors.idle}`}>
      {labels[status] ?? status}
    </span>
  )
}
