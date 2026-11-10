import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import type { GuardEventTrace, GuardLayerInfo } from '../api'
import {
  DefenseFlowGraph,
  LAYER_ROLE,
  S1_LAYER_ORDER,
  S2_STAGE_ORDER,
  STAGE_META,
  resolveLayerId,
  stageStatus,
} from './DefenseFlowGraph'
import type { LayerStatus, StageId } from './DefenseFlowGraph'

const STAGE_INDEX: Record<StageId, string> = {
  user_input: 'S1.1',
  retrieved_context: 'S1.2',
  tool_output: 'S1.3',
  planner: 'S2.1',
  pinned_plan: 'S2.2',
}

function statusLabel(status: LayerStatus) {
  if (status === 'idle') return 'standby'
  if (status === 'planned') return 'in path'
  return status
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
  const [selected, setSelected] = useState<StageId>('planner')

  const stages = useMemo(() => {
    const byId = new Map(guardLayers.map((layer) => [layer.id, layer]))
    return [...S1_LAYER_ORDER, ...S2_STAGE_ORDER].map((id) => {
      const fallback = STAGE_META[id]
      const fromApi = byId.get(id)
      return {
        id,
        label: fromApi?.label ?? fallback.label,
        enabled: fromApi?.enabled ?? fallback.enabled,
        description: fromApi?.description ?? fallback.description,
      }
    })
  }, [guardLayers])

  const selectedMeta = stages.find((stage) => stage.id === selected) ?? stages[0]
  const selectedId = resolveLayerId(selectedMeta.id)
  const selectedStatus = stageStatus(selectedId, events)
  const selectedEvents =
    selectedId === 'planner' || selectedId === 'pinned_plan'
      ? []
      : events.filter((event) => event.layer === selectedId)
  const latest = selectedEvents[selectedEvents.length - 1]
  const recent = [...events].reverse().slice(0, 5)
  const isS2 = selectedId === 'planner' || selectedId === 'pinned_plan'

  return (
    <section className="panel defense-panel defense-panel-bottom">
      <div className="panel-head">
        <h2>Full defense flow · S1 + S2</h2>
        <span>{decisionModel || 'decision model'} · planner</span>
      </div>

      <div className="defense-body">
      <DefenseFlowGraph
        guardLayers={guardLayers}
        events={events}
        selected={selected}
        onSelect={setSelected}
        decisionModel={decisionModel}
      />

      <div className="flow-dock">
        <div className="flow-gates" role="group" aria-label="Defense stages">
          {stages.map((stage) => {
            const id = resolveLayerId(stage.id)
            const status = stageStatus(id, events)
            const hot =
              id !== 'planner' &&
              id !== 'pinned_plan' &&
              events.some((event) => event.layer === id && event.injection)
            return (
              <button
                key={stage.id}
                type="button"
                aria-pressed={selected === id}
                className={`flow-gate ${selected === id ? 'is-on' : ''} is-${status} ${hot ? 'is-hot' : ''}`}
                onClick={() => setSelected(id)}
              >
                <span className="flow-gate-idx">{STAGE_INDEX[id]}</span>
                <span className="flow-gate-copy">
                  <strong>{stage.label}</strong>
                  <em>{stage.enabled ? LAYER_ROLE[id] : 'Off'}</em>
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
              {STAGE_INDEX[selectedId]} · {LAYER_ROLE[selectedId]}
            </p>
            <h3>{selectedMeta.label}</h3>
            <p>{selectedMeta.description}</p>
            <div className="flow-meta">
              <span className={selectedMeta.enabled ? 'is-live' : 'is-off'}>
                {selectedMeta.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <span className={`flow-pill ${selectedStatus}`}>{statusLabel(selectedStatus)}</span>
              {!isS2 ? (
                <span>{latest ? `noul ${latest.confidence.toFixed(3)}` : 'noul —'}</span>
              ) : (
                <span>no tools on planner</span>
              )}
            </div>
            {isS2 ? (
              <p className="flow-reason">
                {selectedId === 'planner'
                  ? 'P-LLM drafts the sequence from the user goal + schemas. Retrieved content is still unread.'
                  : 'Once pinned, the executor may only run these steps. Poisoned docs cannot add send_email or change the plan.'}
              </p>
            ) : latest ? (
              <p className="flow-reason">{latest.reason}</p>
            ) : (
              <p className="flow-reason is-empty">
                Armed and waiting. Run a query to score this choke point.
              </p>
            )}
          </motion.article>

          <article className="flow-card flow-log">
            <div className="flow-log-head">
              <h3>Recent S1 verdicts</h3>
              <span>{events.length === 0 ? 'quiet' : 'live'}</span>
            </div>
            {recent.length === 0 ? (
              <p className="flow-reason is-empty">
                S1 yes = injection → block/drop. S1 no → S2 planner pins the plan, then content is
                fetched under that plan.
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
      </div>
    </section>
  )
}
