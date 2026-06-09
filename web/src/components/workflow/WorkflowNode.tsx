import type { LayoutNode } from './graphLayout'
import { NODE_W, NODE_H, NODE_R } from './graphLayout'

type NodeStatus = 'idle' | 'active' | 'visited'

const colors = {
  idle:    { fill: '#15233e', stroke: '#2a3f65', text: '#8097bf', agentBg: '#1a2c4a' },
  active:  { fill: '#122840', stroke: '#49c6e5', text: '#e8eefc', agentBg: '#1a3850' },
  visited: { fill: '#132e20', stroke: '#2f8a5a', text: '#a8dbc0', agentBg: '#1a3d2a' },
}

interface Props {
  node: LayoutNode
  status: NodeStatus
}

export function WorkflowNode({ node, status }: Props) {
  const c = colors[status]
  const cx = node.x + NODE_W / 2
  const isTerminal = node.id === 'approved'

  return (
    <g className={status === 'active' ? 'node-active-glow' : ''}>
      <rect
        x={node.x} y={node.y}
        width={NODE_W} height={NODE_H}
        rx={NODE_R}
        fill={status === 'visited' && isTerminal ? '#2a2a14' : c.fill}
        stroke={status === 'visited' && isTerminal ? '#d4a017' : c.stroke}
        strokeWidth={status === 'active' ? 2 : 1.2}
      />
      <text
        x={cx} y={node.y + (node.agent ? 19 : 24)}
        textAnchor="middle"
        fill={status === 'visited' && isTerminal ? '#ffd166' : c.text}
        fontSize="13" fontWeight="600"
      >
        {isTerminal && status === 'visited' ? '\u5df2\u901a\u8fc7 \u2713' : node.label}
      </text>
      {node.agent && (
        <>
          <rect
            x={cx - 24} y={node.y + 26}
            width="48" height="16" rx="4"
            fill={c.agentBg} stroke={c.stroke} strokeWidth="0.5"
          />
          <text
            x={cx} y={node.y + 38}
            textAnchor="middle"
            fill={c.text} fontSize="9.5" fontWeight="500" opacity="0.85"
          >
            {node.agent}
          </text>
        </>
      )}
    </g>
  )
}
