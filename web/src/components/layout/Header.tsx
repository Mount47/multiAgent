import { useEffect, useState } from 'react'
import { fetchHealth } from '../../api/client'

export function Header() {
  const [healthy, setHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    const check = () => {
      fetchHealth().then(() => setHealthy(true)).catch(() => setHealthy(false))
    }
    check()
    const t = setInterval(check, 15000)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-line">
      <h1 className="text-base font-bold tracking-wide m-0">Multi-Agent Dev Console</h1>
      <div className="flex items-center gap-2 text-[12px] text-muted">
        <span>Backend</span>
        <span
          className={`w-2 h-2 rounded-full ${
            healthy === null ? 'bg-muted' : healthy ? 'bg-ok' : 'bg-err'
          }`}
        />
      </div>
    </header>
  )
}
