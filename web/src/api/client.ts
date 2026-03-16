import { API } from './endpoints'
import type {
  CreateTaskRequest,
  CreateTaskResponse,
  TaskSummary,
  TaskDetail,
  ProviderItem,
  WorkflowGraphResponse,
  MetricsResponse,
  TraceResponse,
  WorkspaceFile,
} from '../types/api'

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text() || `${res.status}`)
  return res.json()
}

export const fetchProviders = () => get<ProviderItem[]>(API.PROVIDERS)

export const fetchDefaultProvider = () =>
  get<{ default_provider: string }>(API.PROVIDERS_DEFAULT)

export const createTask = (req: CreateTaskRequest) =>
  post<CreateTaskResponse>(API.TASKS, req)

export const fetchTasks = () => get<TaskSummary[]>(API.TASKS)

export const fetchTaskDetail = (id: string) =>
  get<TaskDetail>(API.TASK_DETAIL(id))

export const fetchWorkflowGraph = () =>
  get<WorkflowGraphResponse>(API.WORKFLOW_GRAPH)

export const fetchMetrics = () => get<MetricsResponse>(API.METRICS)

export const fetchTrace = (id: string) =>
  get<TraceResponse>(API.TRACE(id))

export const fetchWorkspaceFiles = () =>
  get<WorkspaceFile[]>(API.WORKSPACE_FILES)

export const fetchHealth = () =>
  get<{ status: string }>(API.HEALTH)
