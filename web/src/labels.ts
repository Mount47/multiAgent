// Centralized Chinese display labels for workflow states, agent roles, and task statuses.
// Backend keeps English identifiers; these map them to Chinese for the UI only.

export const STATE_LABELS: Record<string, string> = {
  requirements_analysis: '需求分析',
  architecture_design: '架构设计',
  coding: '编码',
  testing: '测试',
  code_review: '代码评审',
  revision: '修订',
  approved: '已通过',
}

export const AGENT_LABELS: Record<string, string> = {
  product_manager: '产品经理',
  architect: '架构师',
  coder: '程序员',
  tester: '测试',
  reviewer: '评审',
  user: '用户',
  system: '系统',
  system_error: '系统错误',
}

export const STATUS_LABELS: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  idle: '空闲',
  waiting_approval: '等待确认',
}

export const stateLabel = (s: string): string => STATE_LABELS[s] ?? s.replace(/_/g, ' ')
export const agentLabel = (a: string): string => AGENT_LABELS[a] ?? a
export const statusLabel = (s: string): string => STATUS_LABELS[s] ?? s
