import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import type { GuardEventTrace, GuardLayerInfo } from '../api'
import { DefenseLayersScene } from './DefenseLayersScene'
import type { LayerId } from './DefenseLayersScene'

const FALLBACK_LAYERS: GuardLayerInfo[] = [
  {
    id: 'user_input',
    label: 'User input',
    enabled: true,
    description: 'Decision model scores the user message before the agent runs.',
  },
  {
    id: 'retrieved_context',
    label: 'Retrieved context',
    enabled: true,
    description:
      'Scores search_docs / read_email / read_ticket text before it enters context.',
  },
  {
    id: 'tool_output',
    label: 'Tool output',
    enabled: true,
    description:
      'Scores other tool results (e.g. write-tool confirmations) before re-entry.',
  },
]

export function DefenseLayersPanel({
  guardLayers,
  decisionModel,
  events,
}: {
  guardLayers: GuardLayerInfo[]
  decisionModel: string
  events: GuardEventTrace[]
}) {
  const layers = guardLayers.length > 0 ? guardLayers : FALLBACK_LAYERS
  const [selected, setSelected] = useState<LayerId | null>('user_input')

  const selectedMeta = useMemo(
    () => layers.find((layer) => layer.id === selected) ?? layers[0],
    [layers, selected],
  )

  const selectedEvents = useMemo(
    () => events.filter((event) => event.layer === selected),
    [events, selected],
  )

  return (
    <section className="panel defense-panel">
      <div className="panel-head">
        <h2>S1 defense layers</h2>
        <span>{decisionModel || 'decision model'}</span>
      </div>

      <div className="defense-grid">
        <div className="defense-viz">
          <DefenseLayersScene
            guardLayers={layers}
            events={events}
            selected={selected}
            onSelect={setSelected}
          />
          <p className="viz-hint">Drag to orbit · click a layer slab to inspect</p>
        </div>

        <div className="defense-side">
          <div className="layer-list">
            {layers.map((layer) => {
              const layerEvents = events.filter((event) => event.layer === layer.id)
              const hot = layerEvents.some((event) => event.injection)
              return (
                <button
                  key={layer.id}
                  type="button"
                  className={`layer-row ${selected === layer.id ? 'active' : ''} ${hot ? 'hot' : ''}`}
                  onClick={() => setSelected(layer.id as LayerId)}
                >
                  <div>
                    <strong>{layer.label}</strong>
                    <span>{layer.enabled ? 'enabled' : 'disabled'}</span>
                  </div>
                  <em>
                    {layerEvents.length
                      ? `${layerEvents.length} event(s)`
                      : 'waiting'}
                  </em>
                </button>
              )
            })}
          </div>

          <motion.div
            key={selectedMeta?.id}
            className="layer-detail"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3>{selectedMeta?.label}</h3>
            <p>{selectedMeta?.description}</p>
            {selectedEvents.length === 0 ? (
              <p className="empty">
                Run a query to see live decision-model verdicts on this layer.
              </p>
            ) : (
              <ul className="event-list">
                {selectedEvents.map((event, index) => (
                  <li key={`${event.layer}-${index}`} className={`event ${event.action}`}>
                    <div>
                      <code>{event.action}</code>
                      <span>noul {event.confidence.toFixed(3)}</span>
                    </div>
                    <p>{event.reason}</p>
                    {event.tool_name ? <small>tool: {event.tool_name}</small> : null}
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
