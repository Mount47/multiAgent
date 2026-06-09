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
  if (!metrics) return <EmptyState message="暂无指标数据，请先运行一个任务。" />

  const completionRate = metrics.total_workflows > 0
    ? Math.round((metrics.completed_workflows / metrics.total_workflows) * 100)
    : 0

  return (
    <div className="flex flex-col gap-3 h-[74vh] overflow-y-auto">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="总工作流数" value={metrics.total_workflows} color="text-accent" />
        <StatCard label="完成率" value={`${completionRate}%`} color="text-ok" />
        <StatCard label="平均耗时" value={`${Math.round(metrics.avg_duration_ms)}ms`} />
        <StatCard label="预估 Token" value={metrics.total_estimated_tokens.toLocaleString()} color="text-warn" />
      </div>
      <AgentCallChart data={metrics.agent_call_counts} title="各 Agent 调用次数" />
      <StateDurationChart data={metrics.state_avg_duration_ms} />
      <div className="text-[11px] text-muted text-right">
        运行时长：{Math.round(metrics.uptime_seconds)}s ｜ 状态转移：{metrics.total_state_transitions} 次
      </div>
    </div>
  )
}
