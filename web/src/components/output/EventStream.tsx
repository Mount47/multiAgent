import { useEffect, useRef } from 'react'
import { EventItem } from './EventItem'
import { EmptyState } from '../common/EmptyState'
import type { TaskEvent } from '../../types/api'

interface Props {
  events: TaskEvent[]
}

export function EventStream({ events }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [events])

  return (
    <div
      ref={ref}
      className="h-[74vh] overflow-auto bg-deep-bg rounded-[10px] p-3 border border-line text-[13px] leading-relaxed"
    >
      {events.length === 0 ? (
        <EmptyState message="启动任务后，这里会实时显示各 Agent 的输出。" />
      ) : (
        events.map((ev, i) => (
          <EventItem key={`${ev.timestamp}-${i}`} timestamp={ev.timestamp} source={ev.source} content={ev.content} />
        ))
      )}
    </div>
  )
}
