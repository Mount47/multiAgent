import type { ProviderItem } from '../../types/api'

interface Props {
  providers: ProviderItem[]
  value: string
  onChange: (v: string) => void
}

export function ProviderSelect({ providers, value, onChange }: Props) {
  return (
    <div>
      <label className="block text-muted text-[13px] mb-1">Model Provider</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-[10px] border border-line bg-input-bg text-text p-2.5 text-sm"
      >
        {providers.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name} ({p.model})
          </option>
        ))}
      </select>
    </div>
  )
}
