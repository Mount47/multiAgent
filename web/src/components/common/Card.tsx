import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-panel/92 border border-line rounded-[14px] p-3.5 ${className}`}>
      {children}
    </div>
  )
}
