interface Props {
  label: string
  value: string | number
  color?: string
}

export function StatCard({ label, value, color = 'text-text' }: Props) {
  return (
    <div className="bg-deep-bg border border-line rounded-xl p-4">
      <div className="text-muted text-[12px] mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  )
}
