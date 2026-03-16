import { useState, useCallback } from 'react'
import { Header } from './components/layout/Header'
import { AppShell } from './components/layout/AppShell'
import { Card } from './components/common/Card'
import { TaskForm } from './components/controls/TaskForm'
import { TaskHistory } from './components/tasks/TaskHistory'
import { WorkflowGraph } from './components/workflow/WorkflowGraph'
import { EventStream } from './components/output/EventStream'
import { CodeResultPanel } from './components/code/CodeResultPanel'
import { MetricsDashboard } from './components/metrics/MetricsDashboard'
import { TraceTimeline } from './components/trace/TraceTimeline'
import { useTaskStream } from './hooks/useTaskStream'

type CenterTab = 'workflow' | 'metrics' | 'trace'
type RightTab = 'output' | 'code'

function TabBar<T extends string>({ tabs, active, onChange }: { tabs: T[]; active: T; onChange: (t: T) => void }) {
  return (
    <div className="flex gap-1 mb-2">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-3 py-1.5 rounded-lg text-[13px] font-medium border-none cursor-pointer transition-colors ${
            t === active
              ? 'bg-accent/15 text-accent'
              : 'bg-transparent text-muted hover:text-text'
          }`}
        >
          {t.charAt(0).toUpperCase() + t.slice(1)}
        </button>
      ))}
    </div>
  )
}

export default function App() {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [centerTab, setCenterTab] = useState<CenterTab>('workflow')
  const [rightTab, setRightTab] = useState<RightTab>('output')

  const stream = useTaskStream(taskId)

  const handleTaskCreated = useCallback((id: string) => {
    setTaskId(id)
    setCenterTab('workflow')
    setRightTab('output')
  }, [])

  const handleTaskSelect = useCallback((id: string) => {
    setTaskId(id)
  }, [])

  const sidebar = (
    <>
      <Card>
        <TaskForm onTaskCreated={handleTaskCreated} status={stream.status} taskId={taskId} />
      </Card>
      <Card>
        <TaskHistory selectedTaskId={taskId} onSelect={handleTaskSelect} />
      </Card>
    </>
  )

  const center = (
    <Card>
      <TabBar tabs={['workflow', 'metrics', 'trace'] as CenterTab[]} active={centerTab} onChange={setCenterTab} />
      {centerTab === 'workflow' && (
        <div className="bg-deep-bg rounded-[10px] p-3 border border-line">
          <WorkflowGraph activeState={stream.activeState} visitedStates={stream.visitedStates} />
        </div>
      )}
      {centerTab === 'metrics' && <MetricsDashboard enabled={centerTab === 'metrics'} />}
      {centerTab === 'trace' && <TraceTimeline taskId={taskId} />}
    </Card>
  )

  const right = (
    <Card>
      <TabBar tabs={['output', 'code'] as RightTab[]} active={rightTab} onChange={setRightTab} />
      {rightTab === 'output' && <EventStream events={stream.events} />}
      {rightTab === 'code' && <CodeResultPanel />}
      {stream.error && <div className="text-err text-[13px] mt-2">{stream.error}</div>}
    </Card>
  )

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <AppShell sidebar={sidebar} center={center} right={right} />
    </div>
  )
}
