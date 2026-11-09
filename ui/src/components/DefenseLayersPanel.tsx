import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { GuardEventTrace, GuardLayerInfo } from '../api'
import {
  DefenseLayersScene,
  LAYER_META,
  LAYER_ORDER,
  getLayerStatus,
} from './DefenseLayersScene'
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
  const [selected, setSelected] = useState<LayerId>('user_input')
  const [fullscreen, setFullscreen] = useState(false)
  const stageRef = useRef<HTMLDivElement | null>(null)

  const selectedMeta = useMemo(
    () => layers.find((layer) => layer.id === selected) ?? layers[0],
    [layers, selected],
  )

  const selectedEvents = useMemo(
    () => events.filter((event) => event.layer === selected),
    [events, selected],
  )

  const selectedStatus = getLayerStatus(selected, events)

  const syncFullscreen = useCallback(() => {
    setFullscreen(document.fullscreenElement === stageRef.current)
  }, [])

  useEffect(() => {
    document.addEventListener('fullscreenchange', syncFullscreen)
    return () => document.removeEventListener('fullscreenchange', syncFullscreen)
  }, [syncFullscreen])

  async function toggleFullscreen() {
    const node = stageRef.current
    if (!node) return
    try {
      if (document.fullscreenElement === node) await document.exitFullscreen()
      else await node.requestFullscreen()
    } catch {
      // ignore permission errors
    }
  }

  return (
    <section className="panel defense-panel">
      <div
        ref={stageRef}
        className={`defense-stage ${fullscreen ? 'is-fs' : ''}`}
      >
        <DefenseLayersScene
          guardLayers={layers}
          events={events}
          selected={selected}
          onSelect={setSelected}
        />

        <div className="viz-overlay">
          <div className="viz-top">
            <div className="viz-brand">
              <p>InjectGuard · S1</p>
              <h3>Decision gates</h3>
              <small>Model {decisionModel || 'tev1'} scanning three choke points</small>
            </div>

            <div className="viz-switch">
              {LAYER_ORDER.map((id) => {
                const meta = layers.find((layer) => layer.id === id)
                const status = getLayerStatus(id, events)
                return (
                  <button
                    key={id}
                    type="button"
                    className={`viz-gate is-${status} ${selected === id ? 'is-on' : ''} ${status !== 'idle' ? 'is-hot' : ''}`}
                    onClick={() => setSelected(id)}
                  >
                    <span className="viz-gate-idx">{LAYER_META[id].short}</span>
                    <span>
                      <strong>{meta?.label ?? LAYER_META[id].label}</strong>
                      <em>{status}</em>
                    </span>
                    <i className={`viz-dot ${status}`} />
                  </button>
                )
              })}
            </div>

            <button type="button" className="viz-fs" onClick={toggleFullscreen}>
              <i />
              {fullscreen ? 'Exit' : 'Fullscreen'}
            </button>
          </div>

          <div className="viz-dock">
            <div className="viz-card viz-detail">
              <p className="viz-kicker">Selected gate</p>
              <h3>{selectedMeta?.label}</h3>
              <p>{selectedMeta?.description}</p>
              <div className="viz-meta">
                <span className={selectedMeta?.enabled ? 'is-live' : 'is-off'}>
                  {selectedMeta?.enabled ? 'enabled' : 'disabled'}
                </span>
                <span className={`viz-pill ${selectedStatus}`}>{selectedStatus}</span>
                {selectedEvents[0] ? (
                  <span>noul {selectedEvents[0].confidence.toFixed(3)}</span>
                ) : null}
              </div>
              <p className={`viz-reason ${selectedEvents.length ? '' : 'is-empty'}`}>
                {selectedEvents[0]?.reason ??
                  'Run a query to light this ring with a live verdict.'}
              </p>
            </div>

            <div className="viz-card viz-log">
              <div className="viz-log-head">
                <h3>Gate log</h3>
                <span>{events.length} event(s)</span>
              </div>
              <ul className="viz-events">
                {events.length === 0 ? (
                  <li className="viz-event">
                    <p>No guard events yet.</p>
                  </li>
                ) : (
                  [...events].reverse().slice(0, 8).map((event, index) => (
                    <li
                      key={`${event.layer}-${index}-${event.confidence}`}
                      className={`viz-event ${event.action}`}
                    >
                      <div>
                        <code>{event.action}</code>
                        <em>{event.layer}</em>
                        <span>noul {event.confidence.toFixed(3)}</span>
                      </div>
                      <p>{event.reason}</p>
                      {event.tool_name ? <small>tool: {event.tool_name}</small> : null}
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
