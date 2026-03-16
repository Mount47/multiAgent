export const API = {
  TASKS: '/api/tasks',
  TASK_DETAIL: (id: string) => `/api/tasks/${id}`,
  TASK_WS: (id: string) => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${window.location.host}/api/tasks/ws/${id}`
  },
  PROVIDERS: '/api/providers',
  PROVIDERS_DEFAULT: '/api/providers/default',
  WORKFLOW_GRAPH: '/api/workflow/graph',
  METRICS: '/api/metrics',
  TRACE: (id: string) => `/api/traces/${id}`,
  WORKSPACE_FILES: '/api/workspace/files',
  HEALTH: '/healthz',
} as const
