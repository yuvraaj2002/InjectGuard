import type { GuardEventTrace, GuardLayerInfo } from '../api'

export type LayerId = 'user_input' | 'retrieved_context' | 'tool_output'
export type LayerStatus = 'idle' | 'allow' | 'block' | 'drop' | 'flag'

export const LAYER_ORDER: LayerId[] = ['user_input', 'retrieved_context', 'tool_output']

export const LAYER_ROLE: Record<LayerId, string> = {
  user_input: 'Gate',
  retrieved_context: 'Filter',
  tool_output: 'Filter',
}

export function layerStatus(layer: LayerId, events: GuardEventTrace[]): LayerStatus {
  const hit = [...events].reverse().find((event) => event.layer === layer)
  return hit?.action ?? 'idle'
}

function isLayerId(id: string): id is LayerId {
  return id === 'user_input' || id === 'retrieved_context' || id === 'tool_output'
}

type NodeKind = 'input' | 'decision' | 'block' | 'continue' | 'layer' | 'reply'

type GraphNode = {
  id: string
  label: string
  sub?: string
  kind: NodeKind
  layer?: LayerId
  x: number
  y: number
  w: number
  h: number
}

type GraphEdge = {
  id: string
  from: string
  to: string
  label?: string
  tone?: 'yes' | 'no' | 'neutral'
}

const NODES: GraphNode[] = [
  { id: 'user', label: 'User input', sub: 'request text', kind: 'input', x: 40, y: 48, w: 150, h: 56 },
  {
    id: 'dm1',
    label: 'Decision model',
    sub: 'injection?',
    kind: 'decision',
    layer: 'user_input',
    x: 250,
    y: 40,
    w: 170,
    h: 72,
  },
  { id: 'block', label: 'Blocked', sub: 'refuse request', kind: 'block', x: 500, y: 8, w: 140, h: 52 },
  {
    id: 'agent',
    label: 'Agent loop',
    sub: 'tools + model',
    kind: 'continue',
    x: 500,
    y: 96,
    w: 140,
    h: 56,
  },
  {
    id: 'ctx',
    label: 'Retrieved context',
    sub: 'docs · email · ticket',
    kind: 'layer',
    layer: 'retrieved_context',
    x: 700,
    y: 48,
    w: 168,
    h: 64,
  },
  {
    id: 'dm2',
    label: 'Decision model',
    sub: 'poisoned?',
    kind: 'decision',
    layer: 'retrieved_context',
    x: 920,
    y: 40,
    w: 170,
    h: 72,
  },
  { id: 'drop', label: 'Drop / flag', sub: 'withhold text', kind: 'block', x: 1150, y: 8, w: 140, h: 52 },
  {
    id: 'tools',
    label: 'Tool output',
    sub: 'write / other tools',
    kind: 'layer',
    layer: 'tool_output',
    x: 1150,
    y: 96,
    w: 140,
    h: 56,
  },
  {
    id: 'dm3',
    label: 'Decision model',
    sub: 'safe?',
    kind: 'decision',
    layer: 'tool_output',
    x: 1340,
    y: 88,
    w: 160,
    h: 72,
  },
  { id: 'reply', label: 'Reply', sub: 'final answer', kind: 'reply', x: 1560, y: 96, w: 120, h: 56 },
]

const EDGES: GraphEdge[] = [
  { id: 'e1', from: 'user', to: 'dm1', tone: 'neutral' },
  { id: 'e2', from: 'dm1', to: 'block', label: 'yes', tone: 'yes' },
  { id: 'e3', from: 'dm1', to: 'agent', label: 'no', tone: 'no' },
  { id: 'e4', from: 'agent', to: 'ctx', tone: 'neutral' },
  { id: 'e5', from: 'ctx', to: 'dm2', tone: 'neutral' },
  { id: 'e6', from: 'dm2', to: 'drop', label: 'yes', tone: 'yes' },
  { id: 'e7', from: 'dm2', to: 'tools', label: 'no', tone: 'no' },
  { id: 'e8', from: 'tools', to: 'dm3', tone: 'neutral' },
  { id: 'e9', from: 'dm3', to: 'reply', label: 'pass', tone: 'no' },
]

function nodeCenter(node: GraphNode) {
  return { x: node.x + node.w / 2, y: node.y + node.h / 2 }
}

function edgePath(from: GraphNode, to: GraphNode) {
  const a = nodeCenter(from)
  const b = nodeCenter(to)
  const startX = from.x + from.w
  const startY = a.y
  const endX = to.x
  const endY = b.y
  const midX = (startX + endX) / 2
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`
}

function edgeLabelPoint(from: GraphNode, to: GraphNode) {
  const a = nodeCenter(from)
  const b = nodeCenter(to)
  return {
    x: (from.x + from.w + to.x) / 2,
    y: (a.y + b.y) / 2 - 10,
  }
}

export function DefenseFlowGraph({
  events,
  selected,
  onSelect,
  decisionModel,
}: {
  guardLayers: GuardLayerInfo[]
  events: GuardEventTrace[]
  selected: LayerId
  onSelect: (id: LayerId) => void
  decisionModel: string
}) {
  const statuses: Record<LayerId, LayerStatus> = {
    user_input: layerStatus('user_input', events),
    retrieved_context: layerStatus('retrieved_context', events),
    tool_output: layerStatus('tool_output', events),
  }

  const activeEdgeIds = new Set<string>()
  if (statuses.user_input === 'block') activeEdgeIds.add('e2')
  else if (statuses.user_input === 'allow') {
    activeEdgeIds.add('e3')
    activeEdgeIds.add('e4')
  }
  if (statuses.retrieved_context === 'drop' || statuses.retrieved_context === 'flag') {
    activeEdgeIds.add('e6')
  } else if (statuses.retrieved_context === 'allow') {
    activeEdgeIds.add('e7')
    activeEdgeIds.add('e8')
  }
  if (statuses.tool_output === 'allow' || statuses.tool_output === 'flag') {
    activeEdgeIds.add('e9')
  }
  if (events.length > 0) activeEdgeIds.add('e1')
  if (statuses.retrieved_context !== 'idle' || statuses.tool_output !== 'idle') {
    activeEdgeIds.add('e5')
  }

  return (
    <div className="flow-graph" aria-label="S1 defense flow graph">
      <div className="flow-graph-scroll">
        <svg viewBox="0 0 1720 180" role="img" aria-labelledby="flow-title">
          <title id="flow-title">
            User input through decision model gates to agent loop and reply
          </title>

          <defs>
            <marker
              id="arrow-neutral"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#6d7b88" />
            </marker>
            <marker
              id="arrow-yes"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#b42318" />
            </marker>
            <marker
              id="arrow-no"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#0b7f8a" />
            </marker>
          </defs>

          {EDGES.map((edge) => {
            const from = NODES.find((n) => n.id === edge.from)!
            const to = NODES.find((n) => n.id === edge.to)!
            const active = activeEdgeIds.has(edge.id)
            const labelAt = edge.label ? edgeLabelPoint(from, to) : null
            const marker =
              edge.tone === 'yes'
                ? 'url(#arrow-yes)'
                : edge.tone === 'no'
                  ? 'url(#arrow-no)'
                  : 'url(#arrow-neutral)'
            return (
              <g key={edge.id} className={`flow-edge tone-${edge.tone ?? 'neutral'} ${active ? 'is-active' : ''}`}>
                <path d={edgePath(from, to)} markerEnd={marker} />
                {edge.label && labelAt ? (
                  <text x={labelAt.x} y={labelAt.y} textAnchor="middle">
                    {edge.label}
                  </text>
                ) : null}
              </g>
            )
          })}

          {NODES.map((node) => {
            const selectable = Boolean(node.layer)
            const status = node.layer ? statuses[node.layer] : 'idle'
            const isSelected = node.layer === selected
            const className = [
              'flow-node',
              `kind-${node.kind}`,
              `status-${status}`,
              isSelected ? 'is-selected' : '',
              selectable ? 'is-selectable' : '',
            ]
              .filter(Boolean)
              .join(' ')

            return (
              <g
                key={node.id}
                className={className}
                transform={`translate(${node.x} ${node.y})`}
                role={selectable ? 'button' : undefined}
                tabIndex={selectable ? 0 : undefined}
                onClick={() => {
                  if (node.layer) onSelect(node.layer)
                }}
                onKeyDown={(event) => {
                  if (!node.layer) return
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onSelect(node.layer)
                  }
                }}
              >
                <rect width={node.w} height={node.h} rx={12} ry={12} />
                <text className="flow-node-label" x={node.w / 2} y={node.sub ? 24 : 34} textAnchor="middle">
                  {node.label}
                </text>
                {node.sub ? (
                  <text className="flow-node-sub" x={node.w / 2} y={44} textAnchor="middle">
                    {node.sub}
                  </text>
                ) : null}
                {node.layer && status !== 'idle' ? (
                  <text className="flow-node-status" x={node.w / 2} y={node.h - 10} textAnchor="middle">
                    {status}
                  </text>
                ) : null}
              </g>
            )
          })}
        </svg>
      </div>
      <p className="flow-graph-caption">
        {decisionModel || 'decision model'} scores text at each gate · click a decision /
        layer node for details · yes = injection detected
      </p>
    </div>
  )
}

export function resolveLayerId(id: string): LayerId {
  return isLayerId(id) ? id : 'user_input'
}
