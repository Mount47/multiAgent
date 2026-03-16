import { useState } from 'react'
import { createTask } from '../../api/client'
import { useProviders } from '../../hooks/useProviders'
import { ProviderSelect } from './ProviderSelect'
import { StatusBadge } from './StatusBadge'
import type { TaskStatus } from '../../types/api'

interface Props {
  onTaskCreated: (taskId: string) => void
  status: TaskStatus | 'idle'
  taskId: string | null
}

export function TaskForm({ onTaskCreated, status, taskId }: Props) {
  const { providers, defaultProvider } = useProviders()
  const [text, setText] = useState('Build a Python function that checks if a string is a palindrome, with tests.')
  const [provider, setProvider] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const selectedProvider = provider || defaultProvider

  const handleSubmit = async () => {
    if (!text.trim() || submitting) return
    setError('')
    setSubmitting(true)
    try {
      const res = await createTask({ task: text.trim(), provider: selectedProvider || null })
      onTaskCreated(res.task_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-lg font-bold tracking-wide mb-2">Multi-Agent Console</h1>
      <p className="text-muted text-[13px] mb-3">Create a task and watch agents collaborate in real-time.</p>

      <label className="block text-muted text-[13px] mb-1">Task Description</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="w-full rounded-[10px] border border-line bg-input-bg text-text p-2.5 text-sm min-h-[90px] resize-y"
      />

      <div className="mt-2">
        <ProviderSelect providers={providers} value={selectedProvider} onChange={setProvider} />
      </div>

      <button
        onClick={handleSubmit}
        disabled={submitting || !text.trim()}
        className="w-full mt-3 py-2.5 rounded-[10px] bg-gradient-to-r from-[#2282b3] to-accent text-[#041022] font-bold text-sm cursor-pointer border-none hover:brightness-110 disabled:opacity-50"
      >
        {submitting ? 'Starting...' : 'Start Task'}
      </button>

      <div className="flex justify-between items-center mt-2 text-[12px] text-muted">
        <span>Task ID</span>
        <span className="text-[11px]">{taskId ? taskId.slice(0, 8) : '-'}</span>
      </div>
      <div className="flex justify-between items-center mt-1">
        <span className="text-[12px] text-muted">Status</span>
        <StatusBadge status={status} />
      </div>
      {error && <div className="text-err text-[13px] mt-1.5">{error}</div>}
    </div>
  )
}
