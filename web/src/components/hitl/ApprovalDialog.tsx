import { useState } from 'react'
import type { PendingApproval } from '../../api/useWebSocket'

interface ApprovalDialogProps {
  pending: PendingApproval
  onApprove: () => void
  onRevise: (feedback: string) => void
}

export function ApprovalDialog({ pending, onApprove, onRevise }: ApprovalDialogProps) {
  const [feedback, setFeedback] = useState('')
  const [mode, setMode] = useState<'view' | 'revise'>('view')

  const checkpointLabels: Record<string, string> = {
    architecture_design: '架构设计',
    code_review: '代码评审',
  }

  const agentLabels: Record<string, string> = {
    architect: '架构师',
    reviewer: '代码评审员',
  }

  if (mode === 'revise') {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
          <div className="p-4 border-b bg-amber-50">
            <h3 className="font-semibold text-amber-900">
              请求修改 - {checkpointLabels[pending.checkpoint] || pending.checkpoint}
            </h3>
          </div>

          <div className="p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                修改意见
              </label>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="请输入您的修改意见..."
                className="w-full h-32 p-3 border rounded-md focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
              />
            </div>

            <div className="bg-gray-50 p-3 rounded text-sm">
              <p className="font-medium text-gray-700 mb-1">当前内容预览：</p>
              <pre className="text-gray-600 whitespace-pre-wrap max-h-40 overflow-auto">
                {pending.content.slice(0, 500)}
                {pending.content.length > 500 && '...'}
              </pre>
            </div>
          </div>

          <div className="p-4 border-t flex justify-end gap-3">
            <button
              onClick={() => setMode('view')}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
            >
              返回
            </button>
            <button
              onClick={() => onRevise(feedback)}
              disabled={!feedback.trim()}
              className="px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              提交修改意见
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="p-4 border-b bg-blue-50">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-blue-900">
              等待确认 - {checkpointLabels[pending.checkpoint] || pending.checkpoint}
            </h3>
            <span className="text-sm text-blue-600 bg-blue-100 px-2 py-1 rounded">
              {agentLabels[pending.agent] || pending.agent}
            </span>
          </div>
          <p className="text-sm text-blue-700 mt-1">
            工作流已暂停，请审核以下内容后选择操作
          </p>
        </div>

        <div className="p-4">
          <div className="bg-gray-50 border rounded-md p-4 max-h-96 overflow-auto">
            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono">
              {pending.content}
            </pre>
          </div>
        </div>

        <div className="p-4 border-t flex justify-end gap-3">
          <button
            onClick={() => setMode('revise')}
            className="px-4 py-2 text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-md"
          >
            请求修改
          </button>
          <button
            onClick={onApprove}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            确认通过
          </button>
        </div>
      </div>
    </div>
  )
}
