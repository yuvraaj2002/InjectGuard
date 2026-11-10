import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import type { GuardEventTrace, GuardLayerInfo } from '../api'
import {
  DefenseFlowGraph,
  LAYER_ORDER,
  LAYER_ROLE,
  layerStatus,
  resolveLayerId,
} from './DefenseFlowGraph'
import type { LayerId, LayerStatus } from './DefenseFlowGraph'

const FALLBACK_LAYERS: GuardLayerInfo[] = [
  {
    id: 'user_input',
    label: 'User input',
    enabled: true,
    description: 'Decision model scores the user message before the agent runs. A block refuses the request.',
  },
  {
    id: 'retrieved_context',
    label: 'Retrieved context',
    enabled: true,
    description:
      'Scores search_docs, read_email, and read_ticket text before it enters context. A drop withholds poisoned text.',
  },
  {
    id: 'tool_output',
    label: 'Tool output',
    enabled: true,
    description: 'Scores other tool results before they re-enter the loop. The gate can drop or flag.',
  },
]

const LAYER_INDEX: Record<LayerId, string> = {
  user_input: '01',
  retrieved_context: '02',
  tool_output: '03',
}

function statusLabel(status: LayerStatus) {
  return status === 'idle' ? 'standby' : status
}

export function DefenseLayersPanel({
  guardLayers,
  decisionModel,
  events,
}: {
  guardLayers: GuardLayerInfo[]
  decisionModel: string
  events: GuardEventTrace[]
}) {
  const [selected, setSelected] = useState<LayerId>('user_input')

  const layers = useMemo(() => {
    const source = guardLayers.length > 0 ? guardLayers : FALLBACK_LAYERS
    const byId = new Map(source.map((layer) => [layer.id, layer]))
    return LAYER_ORDER.map((id) => byId.get(id) ?? FALLBACK_LAYERS.find((layer) => layer.id === id)!)
  }, [guardLayers])

  const selectedMeta = layers.find((layer) => layer.id === selected) ?? layers[0]
  const selectedId = resolveLayerId(selectedMeta.id)
  const selectedStatus = layerStatus(selectedId, events)
  const selectedEvents = events.filter((event) => event.layer === selectedId)
  const latest = selectedEvents[selectedEvents.length - 1]
  const recent = [...events].reverse().slice(0, 5)

  return (
    <section className="panel defense-panel">
      <div className="panel-head">
        <h2>S1 defense flow</h2>
        <span>{decisionModel || 'decision model'}</span>
      </div>

      <DefenseFlowGraph
        guardLayers={layers}
        events={events}
        selected={selected}
        onSelect={setSelected}
        decisionModel={decisionModel}
      />

      <div className="flow-dock">
        <div className="flow-gates" role="group" aria-label="Choke points">
          {layers.map((layer) => {
            const id = resolveLayerId(layer.id)
            const status = layerStatus(id, events)
            const hot = events.some((event) => event.layer === id && event.injection)
            return (
              <button
                key={layer.id}
                type="button"
                aria-pressed={selected === id}
                className={`flow-gate ${selected === id ? 'is-on' : ''} is-${status} ${hot ? 'is-hot' : ''}`}
                onClick={() => setSelected(id)}
              >
                <span className="flow-gate-idx">{LAYER_INDEX[id]}</span>
                <span className="flow-gate-copy">
                  <strong>{layer.label}</strong>
                  <em>{layer.enabled ? LAYER_ROLE[id] : 'Off'}</em>
                </span>
                <span className={`flow-dot ${status}`} />
              </button>
            )
          })}
        </div>

        <div className="flow-cards">
          <motion.article
            key={selectedMeta.id}
            className="flow-card"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            <p className="flow-kicker">
              Gate {LAYER_INDEX[selectedId]} · {LAYER_ROLE[selectedId]}
            </p>
            <h3>{selectedMeta.label}</h3>
            <p>{selectedMeta.description}</p>
            <div className="flow-meta">
              <span className={selectedMeta.enabled ? 'is-live' : 'is-off'}>
                {selectedMeta.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <span className={`flow-pill ${selectedStatus}`}>{statusLabel(selectedStatus)}</span>
              <span>{latest ? `noul ${latest.confidence.toFixed(3)}` : 'noul —'}</span>
            </div>
            {latest ? (
              <p className="flow-reason">{latest.reason}</p>
            ) : (
              <p className="flow-reason is-empty">
                Armed and waiting. Run a query to score this choke point.
              </p>
            )}
          </motion.article>

          <article className="flow-card flow-log">
            <div className="flow-log-head">
              <h3>Recent verdicts</h3>
              <span>{events.length === 0 ? 'quiet' : 'live'}</span>
            </div>
            {recent.length === 0 ? (
              <p className="flow-reason is-empty">
                Yes = injection → block/drop. No = continue to the next node in the graph.
              </p>
            ) : (
              <ul className="flow-events">
                {recent.map((event, index) => (
                  <li key={`${event.layer}-${event.action}-${index}`} className={`flow-event ${event.action}`}>
                    <div>
                      <code>{event.action}</code>
                      <span>{event.layer.replaceAll('_', ' ')}</span>
                      <span>noul {event.confidence.toFixed(3)}</span>
                      {event.injection ? <em>injection</em> : null}
                    </div>
                    <p>{event.reason}</p>
                    {event.tool_name ? <small>{event.tool_name}</small> : null}
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>
      </div>
    </section>
  )
}
