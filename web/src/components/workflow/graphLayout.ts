// Workflow graph layout constants and path computation
// Ported from the original react-app.jsx

export const NODE_W = 154
export const NODE_H = 48
export const NODE_R = 8

export interface LayoutNode {
  id: string
  label: string
  agent: string | null
  x: number
  y: number
}

export interface LayoutEdge {
  id: string
  from: string
  to: string
  label: string
  guard?: string
}

export const NODES: LayoutNode[] = [
  { id: 'requirements_analysis', label: 'Requirements', agent: 'PM', x: 173, y: 15 },
  { id: 'architecture_design', label: 'Architecture', agent: 'Architect', x: 173, y: 105 },
  { id: 'coding', label: 'Coding', agent: 'Coder', x: 173, y: 195 },
  { id: 'testing', label: 'Testing', agent: 'Tester', x: 173, y: 285 },
  { id: 'code_review', label: 'Code Review', agent: 'Reviewer', x: 48, y: 390 },
  { id: 'revision', label: 'Revision', agent: 'Coder', x: 298, y: 390 },
  { id: 'approved', label: 'Approved', agent: null, x: 48, y: 500 },
]

export const EDGES: LayoutEdge[] = [
  { id: 'e0', from: 'requirements_analysis', to: 'architecture_design', label: '' },
  { id: 'e1', from: 'architecture_design', to: 'coding', label: '' },
  { id: 'e2', from: 'coding', to: 'testing', label: '' },
  { id: 'e3', from: 'testing', to: 'code_review', label: 'passed', guard: 'tests_passed' },
  { id: 'e4', from: 'testing', to: 'revision', label: 'failed', guard: 'tests_failed' },
  { id: 'e5', from: 'code_review', to: 'approved', label: 'approved', guard: 'review_approved' },
  { id: 'e6', from: 'code_review', to: 'revision', label: 'revise', guard: 'review_revision_needed' },
  { id: 'e7', from: 'revision', to: 'testing', label: '' },
]

const N = Object.fromEntries(NODES.map((n) => [n.id, n]))

const cx = (n: LayoutNode) => n.x + NODE_W / 2
const cy = (n: LayoutNode) => n.y + NODE_H / 2
const bot = (n: LayoutNode) => ({ x: cx(n), y: n.y + NODE_H })
const top_ = (n: LayoutNode) => ({ x: cx(n), y: n.y })
const right_ = (n: LayoutNode) => ({ x: n.x + NODE_W, y: cy(n) })
const left_ = (n: LayoutNode) => ({ x: n.x, y: cy(n) })

export function edgePath(edge: LayoutEdge): string {
  const s = N[edge.from]
  const t = N[edge.to]

  if (edge.from === 'requirements_analysis' || edge.from === 'architecture_design' || edge.from === 'coding') {
    const p1 = bot(s), p2 = top_(t)
    return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`
  }
  if (edge.id === 'e3') {
    const p1 = { x: cx(s) - 30, y: s.y + NODE_H }
    const p2 = { x: cx(t) + 20, y: t.y }
    return `M ${p1.x},${p1.y} C ${p1.x},${p1.y + 40} ${p2.x},${p2.y - 40} ${p2.x},${p2.y}`
  }
  if (edge.id === 'e4') {
    const p1 = { x: cx(s) + 30, y: s.y + NODE_H }
    const p2 = { x: cx(t) - 20, y: t.y }
    return `M ${p1.x},${p1.y} C ${p1.x},${p1.y + 40} ${p2.x},${p2.y - 40} ${p2.x},${p2.y}`
  }
  if (edge.id === 'e5') {
    const p1 = bot(s), p2 = top_(t)
    return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`
  }
  if (edge.id === 'e6') {
    const p1 = right_(s), p2 = left_(t)
    return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`
  }
  if (edge.id === 'e7') {
    const p1 = { x: t.x + NODE_W + 4, y: cy(t) }
    const p2 = top_(s)
    return `M ${p2.x},${p2.y} C ${p2.x + 80},${p2.y - 60} ${p1.x + 30},${p1.y + 50} ${p1.x},${p1.y}`
  }
  const p1 = bot(s), p2 = top_(t)
  return `M ${p1.x},${p1.y} L ${p2.x},${p2.y}`
}

export function edgeLabelPos(edge: LayoutEdge): { x: number; y: number } {
  const s = N[edge.from]
  const t = N[edge.to]
  if (edge.id === 'e3') return { x: (cx(s) - 30 + cx(t) + 20) / 2 - 18, y: (s.y + NODE_H + t.y) / 2 + 4 }
  if (edge.id === 'e4') return { x: (cx(s) + 30 + cx(t) - 20) / 2 + 2, y: (s.y + NODE_H + t.y) / 2 + 4 }
  if (edge.id === 'e5') return { x: cx(s) - 38, y: (bot(s).y + top_(t).y) / 2 + 4 }
  if (edge.id === 'e6') return { x: (right_(s).x + left_(t).x) / 2 - 14, y: cy(s) - 8 }
  return { x: 0, y: 0 }
}
