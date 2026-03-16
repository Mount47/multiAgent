import type { LayoutEdge } from './graphLayout'
import { edgePath, edgeLabelPos } from './graphLayout'

type EdgeStatus = 'idle' | 'active' | 'visited'

const edgeColors = {
  idle: '#2a3f65',
  active: '#49c6e5',
  visited: '#2f8a5a',
}

interface Props {
  edge: LayoutEdge
  status: EdgeStatus
}

export function WorkflowEdge({ edge, status }: Props) {
  const color = edgeColors[status]
  const pos = edgeLabelPos(edge)

  return (
    <g>
      <path
        d={edgePath(edge)}
        stroke={color}
        strokeWidth={status === 'active' ? 2.5 : 1.5}
        fill="none"
        markerEnd={`url(#ah-${status})`}
        style={status === 'active' ? { filter: 'drop-shadow(0 0 4px #49c6e5)' } : {}}
      />
      {edge.label && (
        <text
          x={pos.x} y={pos.y}
          fill={status === 'idle' ? '#5a7099' : color}
          fontSize="11" fontWeight="500"
        >
          {edge.label}
        </text>
      )}
    </g>
  )
}
