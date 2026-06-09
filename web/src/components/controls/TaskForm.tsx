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
  const [text, setText] = useState('编写一个 Python 函数，判断字符串是否为回文，并附带 pytest 测试。')
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
      setError(e instanceof Error ? e.message : '请求失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-lg font-bold tracking-wide mb-2">多 Agent 控制台</h1>
      <p className="text-muted text-[13px] mb-3">创建任务，实时观看多个 Agent 协作。</p>

      <label className="block text-muted text-[13px] mb-1">任务描述</label>
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
        {submitting ? '启动中...' : '开始任务'}
      </button>

      <div className="flex justify-between items-center mt-2 text-[12px] text-muted">
        <span>任务 ID</span>
        <span className="text-[11px]">{taskId ? taskId.slice(0, 8) : '-'}</span>
      </div>
      <div className="flex justify-between items-center mt-1">
        <span className="text-[12px] text-muted">状态</span>
        <StatusBadge status={status} />
      </div>
      {error && <div className="text-err text-[13px] mt-1.5">{error}</div>}
    </div>
  )
}
