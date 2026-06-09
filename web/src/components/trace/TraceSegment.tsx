import { stateLabel, agentLabel } from '../../labels'

const AGENT_COLORS: Record<string, string> = {
  product_manager: '#4a9eff',
  architect: '#c77dff',
  coder: '#41d39c',
  tester: '#ffd166',
  reviewer: '#49c6e5',
}

interface Props {
  fromState: string
  toState: string
  agent: string
  durationMs: number
  tokens: number
  widthPercent: number
}

export function TraceSegment({ fromState, toState, agent, durationMs, tokens, widthPercent }: Props) {
  const color = AGENT_COLORS[agent] || '#49c6e5'
  const label = stateLabel(fromState)

  return (
    <div
      className="group relative h-10 rounded-md flex items-center justify-center overflow-hidden cursor-default transition-opacity hover:opacity-90"
      style={{ width: `${Math.max(widthPercent, 3)}%`, backgroundColor: color + '33', borderLeft: `3px solid ${color}` }}
      title={`${stateLabel(fromState)} → ${stateLabel(toState)}\nAgent：${agentLabel(agent)}\n耗时：${durationMs}ms\nTokens：${tokens}`}
    >
      {widthPercent > 8 && (
        <span className="text-[10px] text-text truncate px-1">{label}</span>
      )}
      <div className="absolute bottom-0 left-0 right-0 bg-black/40 text-[9px] text-muted text-center opacity-0 group-hover:opacity-100 transition-opacity">
        {durationMs}ms | {tokens} tokens
      </div>
    </div>
  )
}
