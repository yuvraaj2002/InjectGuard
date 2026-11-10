import type { GuardEventTrace, GuardLayerInfo } from '../api'

export type S1LayerId = 'user_input' | 'retrieved_context' | 'tool_output'
export type S2StageId = 'planner' | 'pinned_plan'
export type StageId = S1LayerId | S2StageId

export type LayerId = StageId
export type LayerStatus = 'idle' | 'allow' | 'block' | 'drop' | 'flag' | 'planned'

export const S1_LAYER_ORDER: S1LayerId[] = ['user_input', 'retrieved_context', 'tool_output']
export const S2_STAGE_ORDER: S2StageId[] = ['planner', 'pinned_plan']
export const LAYER_ORDER: StageId[] = [...S1_LAYER_ORDER, ...S2_STAGE_ORDER]

export const LAYER_ROLE: Record<StageId, string> = {
  user_input: 'S1 gate',
  retrieved_context: 'S1 filter',
  tool_output: 'S1 filter',
  planner: 'S2 plan',
  pinned_plan: 'S2 pin',
}

export const STAGE_META: Record<
  StageId,
  { label: string; description: string; enabled: boolean }
> = {
  user_input: {
    label: 'User input',
    enabled: true,
    description:
      'Decision model scores the user message before anything else runs. A block refuses the request.',
  },
  retrieved_context: {
    label: 'Retrieved context',
    enabled: true,
    description:
      'Scores search_policies, read_dispute, get_account, list_payees, read_email, and read_ticket text before it enters context. A drop withholds poisoned text.',
  },
  tool_output: {
    label: 'Tool output',
    enabled: true,
    description: 'Scores other tool results before they re-enter the loop. The gate can drop or flag.',
  },
  planner: {
    label: 'Planner LLM',
    enabled: true,
    description:
      'Privileged P-LLM sees the user goal and tool schemas only — no emails, docs, or tickets yet. It writes the control-flow plan before untrusted content is read.',
  },
  pinned_plan: {
    label: 'Pinned plan',
    enabled: true,
    description:
      'Validated JSON steps (tool + args with $variables). Control flow is fixed here so later retrieved text cannot invent new tool calls or rewrite the sequence.',
  },
}

export function layerStatus(layer: S1LayerId, events: GuardEventTrace[]): LayerStatus {
  const hit = [...events].reverse().find((event) => event.layer === layer)
  return hit?.action ?? 'idle'
}

export function stageStatus(stage: StageId, events: GuardEventTrace[]): LayerStatus {
  if (stage === 'planner' || stage === 'pinned_plan') {
    return layerStatus('user_input', events) === 'allow' ? 'planned' : 'idle'
  }
  return layerStatus(stage, events)
}

function isStageId(id: string): id is StageId {
  return (
    id === 'user_input' ||
    id === 'retrieved_context' ||
    id === 'tool_output' ||
    id === 'planner' ||
    id === 'pinned_plan'
  )
}

type NodeKind = 'input' | 'decision' | 'block' | 'planner' | 'plan' | 'layer' | 'reply'

type GraphNode = {
  id: string
  label: string
  sub?: string
  kind: NodeKind
  stage?: StageId
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
  tone?: 'yes' | 'no' | 'neutral' | 's2'
}

type Band = {
  id: string
  label: string
  x: number
  y: number
  w: number
  h: number
}

const CX = 250
const NW = 200
const BRANCH_X = 500

const BANDS: Band[] = [
  { id: 'band-s1a', label: 'S1 · detect', x: 24, y: 16, w: 672, h: 220 },
  { id: 'band-s2', label: 'S2 · isolate', x: 24, y: 248, w: 672, h: 300 },
  { id: 'band-s1b', label: 'S1 · filter content', x: 24, y: 560, w: 672, h: 500 },
]

const NODES: GraphNode[] = [
  { id: 'user', label: 'User input', sub: 'request text', kind: 'input', stage: 'user_input', x: CX, y: 44, w: NW, h: 56 },
  {
    id: 'dm1',
    label: 'Decision model',
    sub: 'injection?',
    kind: 'decision',
    stage: 'user_input',
    x: CX,
    y: 132,
    w: NW,
    h: 68,
  },
  { id: 'block', label: 'Blocked', sub: 'refuse request', kind: 'block', x: BRANCH_X, y: 140, w: 150, h: 52 },
  {
    id: 'planner',
    label: 'Planner LLM',
    sub: 'schemas only · no tools',
    kind: 'planner',
    stage: 'planner',
    x: CX,
    y: 280,
    w: NW,
    h: 68,
  },
  {
    id: 'plan',
    label: 'Pinned plan',
    sub: 'fixed steps · $vars',
    kind: 'plan',
    stage: 'pinned_plan',
    x: CX,
    y: 380,
    w: NW,
    h: 68,
  },
  {
    id: 'exec',
    label: 'Execute',
    sub: 'run pinned steps',
    kind: 'layer',
    x: CX,
    y: 478,
    w: NW,
    h: 56,
  },
  {
    id: 'ctx',
    label: 'Retrieved context',
    sub: 'docs · email · ticket',
    kind: 'layer',
    stage: 'retrieved_context',
    x: CX,
    y: 596,
    w: NW,
    h: 64,
  },
  {
    id: 'dm2',
    label: 'Decision model',
    sub: 'poisoned?',
    kind: 'decision',
    stage: 'retrieved_context',
    x: CX,
    y: 692,
    w: NW,
    h: 68,
  },
  { id: 'drop', label: 'Drop / flag', sub: 'withhold text', kind: 'block', x: BRANCH_X, y: 700, w: 150, h: 52 },
  {
    id: 'tools',
    label: 'Tool output',
    sub: 'write / other tools',
    kind: 'layer',
    stage: 'tool_output',
    x: CX,
    y: 800,
    w: NW,
    h: 56,
  },
  {
    id: 'dm3',
    label: 'Decision model',
    sub: 'safe?',
    kind: 'decision',
    stage: 'tool_output',
    x: CX,
    y: 888,
    w: NW,
    h: 68,
  },
  { id: 'reply', label: 'Reply', sub: 'final answer', kind: 'reply', x: CX, y: 990, w: NW, h: 56 },
]

const EDGES: GraphEdge[] = [
  { id: 'e1', from: 'user', to: 'dm1', tone: 'neutral' },
  { id: 'e2', from: 'dm1', to: 'block', label: 'yes', tone: 'yes' },
  { id: 'e3', from: 'dm1', to: 'planner', label: 'no', tone: 'no' },
  { id: 'e4', from: 'planner', to: 'plan', label: 'pins', tone: 's2' },
  { id: 'e5', from: 'plan', to: 'exec', tone: 's2' },
  { id: 'e6', from: 'exec', to: 'ctx', tone: 'neutral' },
  { id: 'e7', from: 'ctx', to: 'dm2', tone: 'neutral' },
  { id: 'e8', from: 'dm2', to: 'drop', label: 'yes', tone: 'yes' },
  { id: 'e9', from: 'dm2', to: 'tools', label: 'no', tone: 'no' },
  { id: 'e10', from: 'tools', to: 'dm3', tone: 'neutral' },
  { id: 'e11', from: 'dm3', to: 'reply', label: 'pass', tone: 'no' },
]

function nodeCenter(node: GraphNode) {
  return { x: node.x + node.w / 2, y: node.y + node.h / 2 }
}

function isSideBranch(from: GraphNode, to: GraphNode) {
  return to.x >= from.x + from.w - 8
}

function edgePath(from: GraphNode, to: GraphNode) {
  const a = nodeCenter(from)
  const b = nodeCenter(to)

  if (isSideBranch(from, to)) {
    const startX = from.x + from.w
    const startY = a.y
    const endX = to.x
    const endY = b.y
    const midX = (startX + endX) / 2
    return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`
  }

  const startX = a.x
  const startY = from.y + from.h
  const endX = b.x
  const endY = to.y
  const midY = (startY + endY) / 2
  return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`
}

function edgeLabelPoint(from: GraphNode, to: GraphNode) {
  const a = nodeCenter(from)
  const b = nodeCenter(to)

  if (isSideBranch(from, to)) {
    return {
      x: (from.x + from.w + to.x) / 2,
      y: (a.y + b.y) / 2 - 8,
    }
  }

  return {
    x: a.x + 18,
    y: (from.y + from.h + to.y) / 2 + 4,
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
  selected: StageId
  onSelect: (id: StageId) => void
  decisionModel: string
}) {
  const statuses: Record<StageId, LayerStatus> = {
    user_input: stageStatus('user_input', events),
    retrieved_context: stageStatus('retrieved_context', events),
    tool_output: stageStatus('tool_output', events),
    planner: stageStatus('planner', events),
    pinned_plan: stageStatus('pinned_plan', events),
  }

  const activeEdgeIds = new Set<string>()
  if (events.length > 0) activeEdgeIds.add('e1')
  if (statuses.user_input === 'block') activeEdgeIds.add('e2')
  else if (statuses.user_input === 'allow') {
    activeEdgeIds.add('e3')
    activeEdgeIds.add('e4')
    activeEdgeIds.add('e5')
    activeEdgeIds.add('e6')
  }
  if (statuses.retrieved_context === 'drop' || statuses.retrieved_context === 'flag') {
    activeEdgeIds.add('e8')
  } else if (statuses.retrieved_context === 'allow') {
    activeEdgeIds.add('e9')
    activeEdgeIds.add('e10')
  }
  if (statuses.tool_output === 'allow' || statuses.tool_output === 'flag') {
    activeEdgeIds.add('e11')
  }
  if (statuses.retrieved_context !== 'idle' || statuses.tool_output !== 'idle') {
    activeEdgeIds.add('e7')
  }

  return (
    <div className="flow-graph" aria-label="S1 and S2 defense flow graph">
      <div className="flow-graph-scroll">
        <svg viewBox="0 0 720 1080" role="img" aria-labelledby="flow-title">
          <title id="flow-title">
            Vertical defense flow from user input through S1, S2 planner, and content filters
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
            <marker
              id="arrow-s2"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#3d5a80" />
            </marker>
          </defs>

          {BANDS.map((band) => (
            <g key={band.id} className="flow-band">
              <rect x={band.x} y={band.y} width={band.w} height={band.h} rx={16} ry={16} />
              <text x={band.x + 18} y={band.y + 28}>
                {band.label}
              </text>
            </g>
          ))}

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
                  : edge.tone === 's2'
                    ? 'url(#arrow-s2)'
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
            const selectable = Boolean(node.stage)
            const status = node.stage ? statuses[node.stage] : 'idle'
            const isSelected = node.stage === selected
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
                  if (node.stage) onSelect(node.stage)
                }}
                onKeyDown={(event) => {
                  if (!node.stage) return
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onSelect(node.stage)
                  }
                }}
              >
                <rect width={node.w} height={node.h} rx={12} ry={12} />
                <text className="flow-node-label" x={node.w / 2} y={node.sub ? 26 : 34} textAnchor="middle">
                  {node.label}
                </text>
                {node.sub ? (
                  <text className="flow-node-sub" x={node.w / 2} y={44} textAnchor="middle">
                    {node.sub}
                  </text>
                ) : null}
                {node.stage && status !== 'idle' ? (
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
        Top → bottom: S1 ({decisionModel || 'decision model'}) detects, S2 pins the plan, then S1
        filters retrieved content. Click a node for details.
      </p>
    </div>
  )
}

export function resolveLayerId(id: string): StageId {
  return isStageId(id) ? id : 'user_input'
}
