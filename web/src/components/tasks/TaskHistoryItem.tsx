import { StatusBadge } from '../controls/StatusBadge'
import type { TaskSummary } from '../../types/api'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface Props {
  task: TaskSummary
  selected: boolean
  onClick: () => void
}

export function TaskHistoryItem({ task, selected, onClick }: Props) {
  const ago = formatDistanceToNow(new Date(task.created_at), { addSuffix: true, locale: zhCN })

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-2.5 rounded-lg border transition-colors cursor-pointer ${
        selected
          ? 'border-accent bg-accent/10'
          : 'border-transparent hover:border-line hover:bg-panel/50'
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-[12px] text-muted truncate">{task.task_id.slice(0, 8)}</span>
        <StatusBadge status={task.status} />
      </div>
      <div className="text-[13px] truncate">{task.task}</div>
      <div className="text-[11px] text-muted mt-1">{ago}</div>
    </button>
  )
}
