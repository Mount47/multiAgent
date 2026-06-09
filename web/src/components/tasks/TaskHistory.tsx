import { useTasks } from '../../hooks/useTasks'
import { TaskHistoryItem } from './TaskHistoryItem'
import { Spinner } from '../common/Spinner'

interface Props {
  selectedTaskId: string | null
  onSelect: (taskId: string) => void
}

export function TaskHistory({ selectedTaskId, onSelect }: Props) {
  const { tasks, loading, refetch } = useTasks()

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold m-0">历史任务</h2>
        <button
          onClick={refetch}
          className="text-[11px] text-accent bg-transparent border-none cursor-pointer hover:underline"
        >
          刷新
        </button>
      </div>
      {loading ? (
        <div className="flex justify-center py-4"><Spinner /></div>
      ) : tasks.length === 0 ? (
        <div className="text-muted text-[12px] text-center py-3">暂无任务</div>
      ) : (
        <div className="flex flex-col gap-1 max-h-[45vh] overflow-y-auto">
          {tasks.map((t) => (
            <TaskHistoryItem
              key={t.task_id}
              task={t}
              selected={t.task_id === selectedTaskId}
              onClick={() => onSelect(t.task_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
