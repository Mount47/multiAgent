import { useTrace } from '../../hooks/useTrace'
import { TraceSegment } from './TraceSegment'
import { EmptyState } from '../common/EmptyState'
import { Spinner } from '../common/Spinner'

interface Props {
  taskId: string | null
}

export function TraceTimeline({ taskId }: Props) {
  const { trace, loading } = useTrace(taskId)

  if (!taskId) return <EmptyState message="Select a task to view its execution trace." />
  if (loading) return <div className="flex justify-center py-10"><Spinner /></div>
  if (!trace || trace.transitions.length === 0) return <EmptyState message="No trace data for this task." />

  const totalMs = trace.duration_ms || trace.transitions.reduce((s, t) => s + t.duration_ms, 0) || 1

  return (
    <div className="h-[74vh] overflow-y-auto">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[12px] text-muted">
          Total: {Math.round(totalMs)}ms | {trace.total_tokens} tokens | {trace.final_status}
        </div>
      </div>

      <div className="flex gap-0.5 mb-4">
        {trace.transitions.map((t, i) => (
          <TraceSegment
            key={i}
            fromState={t.from_state}
            toState={t.to_state}
            agent={t.agent}
            durationMs={t.duration_ms}
            tokens={t.estimated_tokens}
            widthPercent={(t.duration_ms / totalMs) * 100}
          />
        ))}
      </div>

      <div className="space-y-1.5">
        {trace.transitions.map((t, i) => (
          <div key={i} className="flex items-center gap-3 text-[12px] text-muted">
            <span className="w-5 text-right text-[11px] opacity-60">{i + 1}</span>
            <span className="text-text">{t.from_state.replace(/_/g, ' ')}</span>
            <span className="text-line">→</span>
            <span className="text-text">{t.to_state.replace(/_/g, ' ')}</span>
            <span className="ml-auto">{t.agent}</span>
            <span className="w-16 text-right">{t.duration_ms}ms</span>
            <span className="w-14 text-right">{t.estimated_tokens}t</span>
          </div>
        ))}
      </div>
    </div>
  )
}
