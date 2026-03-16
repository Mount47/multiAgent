import { useMemo } from 'react'

const AGENT_COLORS: Record<string, string> = {
  product_manager: '#4a9eff',
  architect: '#c77dff',
  coder: '#41d39c',
  tester: '#ffd166',
  reviewer: '#49c6e5',
}

interface Props {
  timestamp: string
  source: string
  content: string
}

export function EventItem({ timestamp, source, content }: Props) {
  const time = useMemo(() => new Date(timestamp).toLocaleTimeString(), [timestamp])
  const color = AGENT_COLORS[source] || '#9bb0d9'

  return (
    <div className="mb-2.5 pb-2.5 border-b border-[#14233f]">
      <div className="text-muted text-[12px] mb-0.5">
        [{time}] <span style={{ color }} className="font-semibold">{source}</span>
      </div>
      <div className="text-[13px] leading-relaxed whitespace-pre-wrap">{content}</div>
    </div>
  )
}
