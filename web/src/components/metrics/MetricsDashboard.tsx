import { useMetrics } from '../../hooks/useMetrics'
import { StatCard } from './StatCard'
import { AgentCallChart } from './AgentCallChart'
import { StateDurationChart } from './StateDurationChart'
import { Spinner } from '../common/Spinner'
import { EmptyState } from '../common/EmptyState'

interface Props {
  enabled: boolean
}

export function MetricsDashboard({ enabled }: Props) {
  const { metrics, loading } = useMetrics(enabled)

  if (loading) return <div className="flex justify-center py-10"><Spinner /></div>
  if (!metrics) return <EmptyState message="No metrics available. Run a task first." />

  const completionRate = metrics.total_workflows > 0
    ? Math.round((metrics.completed_workflows / metrics.total_workflows) * 100)
    : 0

  return (
    <div className="flex flex-col gap-3 h-[74vh] overflow-y-auto">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Total Workflows" value={metrics.total_workflows} color="text-accent" />
        <StatCard label="Completion Rate" value={`${completionRate}%`} color="text-ok" />
        <StatCard label="Avg Duration" value={`${Math.round(metrics.avg_duration_ms)}ms`} />
        <StatCard label="Est. Tokens" value={metrics.total_estimated_tokens.toLocaleString()} color="text-warn" />
      </div>
      <AgentCallChart data={metrics.agent_call_counts} title="Agent Call Frequency" />
      <StateDurationChart data={metrics.state_avg_duration_ms} />
      <div className="text-[11px] text-muted text-right">
        Uptime: {Math.round(metrics.uptime_seconds)}s | Transitions: {metrics.total_state_transitions}
      </div>
    </div>
  )
}
