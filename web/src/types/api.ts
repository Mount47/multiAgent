// REST API response types — matches backend Pydantic schemas

export type TaskStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface CreateTaskRequest {
  task: string
  provider?: string | null
}

export interface CreateTaskResponse {
  task_id: string
  status: TaskStatus
}

export interface TaskEvent {
  timestamp: string
  source: string
  content: string
}

export interface TaskSummary {
  task_id: string
  task: string
  provider: string
  status: TaskStatus
  created_at: string
  updated_at: string
  error: string | null
}

export interface TaskDetail extends TaskSummary {
  events: TaskEvent[]
}

export interface ProviderCapabilities {
  vision: boolean
  function_calling: boolean
  json_output: boolean
  family: string
}

export interface ProviderItem {
  name: string
  model: string
  base_url: string
  capabilities: ProviderCapabilities
}

export interface GraphNode {
  id: string
  label: string
  agent: string | null
  position: { x: number; y: number }
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  guard: string
  label: string
}

export interface WorkflowGraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  initial_state: string
}

export interface MetricsResponse {
  total_workflows: number
  completed_workflows: number
  failed_workflows: number
  avg_duration_ms: number
  total_state_transitions: number
  total_estimated_tokens: number
  agent_call_counts: Record<string, number>
  state_avg_duration_ms: Record<string, number>
  uptime_seconds: number
}

export interface TraceTransition {
  from_state: string
  to_state: string
  agent: string
  duration_ms: number
  estimated_tokens: number
}

export interface TraceResponse {
  task_id: string
  started_at: string
  ended_at: string | null
  duration_ms: number
  final_status: string
  total_tokens: number
  transitions: TraceTransition[]
}

export interface WorkspaceFile {
  name: string
  content: string
}
