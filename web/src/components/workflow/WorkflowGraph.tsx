import { NODES, EDGES } from './graphLayout'
import { WorkflowNode } from './WorkflowNode'
import { WorkflowEdge } from './WorkflowEdge'

interface Props {
  activeState: string | null
  visitedStates: Set<string>
}

export function WorkflowGraph({ activeState, visitedStates }: Props) {
  const nodeStatus = (id: string) => {
    if (id === activeState) return 'active' as const
    if (visitedStates.has(id)) return 'visited' as const
    return 'idle' as const
  }

  const edgeStatus = (edge: { from: string; to: string }) => {
    if (edge.to === activeState && (visitedStates.has(edge.from) || edge.from === activeState))
      return 'active' as const
    if (visitedStates.has(edge.from) && visitedStates.has(edge.to))
      return 'visited' as const
    return 'idle' as const
  }

  return (
    <svg viewBox="0 0 500 560" xmlns="http://www.w3.org/2000/svg" className="w-full h-auto">
      <defs>
        <marker id="ah-idle" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0.5, 7 3, 0 5.5" fill="#2a3f65" />
        </marker>
        <marker id="ah-active" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0.5, 7 3, 0 5.5" fill="#49c6e5" />
        </marker>
        <marker id="ah-visited" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0.5, 7 3, 0 5.5" fill="#2f8a5a" />
        </marker>
      </defs>

      {EDGES.map((edge) => (
        <WorkflowEdge key={edge.id} edge={edge} status={edgeStatus(edge)} />
      ))}

      {NODES.map((node) => (
        <WorkflowNode key={node.id} node={node} status={nodeStatus(node.id)} />
      ))}
    </svg>
  )
}
