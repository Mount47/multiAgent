import type { ReactNode } from 'react'

interface Props {
  sidebar: ReactNode
  center: ReactNode
  right: ReactNode
}

export function AppShell({ sidebar, center, right }: Props) {
  return (
    <div className="flex-1 grid grid-cols-[280px_1fr_1fr] gap-3.5 p-4 items-start max-w-[1440px] mx-auto
      max-[1100px]:grid-cols-[1fr_1fr] max-[700px]:grid-cols-1">
      <aside className="flex flex-col gap-3.5 max-[1100px]:col-span-2 max-[700px]:col-span-1">{sidebar}</aside>
      <main className="min-w-0">{center}</main>
      <section className="min-w-0">{right}</section>
    </div>
  )
}
