import type { TaskStatus } from '../../types/api'

const colors: Record<string, string> = {
  queued: 'text-muted border-line',
  running: 'text-accent border-accent',
  completed: 'text-ok border-ok',
  failed: 'text-err border-err',
  idle: 'text-muted border-line',
}

export function StatusBadge({ status }: { status: TaskStatus | 'idle' }) {
  return (
    <span className={`text-xs font-semibold border rounded-full px-2 py-0.5 ${colors[status] ?? colors.idle}`}>
      {status}
    </span>
  )
}
