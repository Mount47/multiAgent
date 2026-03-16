import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#4a9eff', '#c77dff', '#41d39c', '#ffd166', '#49c6e5']

interface Props {
  data: Record<string, number>
  title: string
  valueLabel?: string
}

export function AgentCallChart({ data, title, valueLabel = 'calls' }: Props) {
  const items = Object.entries(data).map(([name, value]) => ({ name, value }))

  if (items.length === 0) return null

  return (
    <div className="bg-deep-bg border border-line rounded-xl p-4">
      <div className="text-muted text-[12px] mb-3">{title}</div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={items} margin={{ top: 0, right: 0, bottom: 0, left: -20 }}>
          <XAxis dataKey="name" tick={{ fill: '#9bb0d9', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#9bb0d9', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#111b2e', border: '1px solid #1f3358', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#e8eefc' }}
            formatter={(v: number) => [`${v} ${valueLabel}`, '']}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {items.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
