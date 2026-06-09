import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { stateLabel } from '../../labels'

const STATE_COLORS: Record<string, string> = {
  requirements_analysis: '#4a9eff',
  architecture_design: '#c77dff',
  coding: '#41d39c',
  testing: '#ffd166',
  code_review: '#49c6e5',
  revision: '#ff6f7d',
}

interface Props {
  data: Record<string, number>
}

export function StateDurationChart({ data }: Props) {
  const items = Object.entries(data).map(([name, value]) => ({
    name: stateLabel(name),
    value: Math.round(value),
    key: name,
  }))

  if (items.length === 0) return null

  return (
    <div className="bg-deep-bg border border-line rounded-xl p-4">
      <div className="text-muted text-[12px] mb-3">各状态平均耗时 (ms)</div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={items} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
          <XAxis dataKey="name" tick={{ fill: '#9bb0d9', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#9bb0d9', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#111b2e', border: '1px solid #1f3358', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#e8eefc' }}
            formatter={(v) => [`${v} ms`, '']}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {items.map((item) => (
              <Cell key={item.key} fill={STATE_COLORS[item.key] || '#49c6e5'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
