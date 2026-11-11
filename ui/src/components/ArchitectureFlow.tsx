import type { GuardEventTrace } from '../api'

type Props = {
  events?: GuardEventTrace[]
}

function latestAction(events: GuardEventTrace[], layer: GuardEventTrace['layer']) {
  const hit = [...events].reverse().find((event) => event.layer === layer)
  return hit?.action ?? null
}

function Connector({ label }: { label?: string }) {
  return (
    <div className="arch-connector" aria-hidden="true">
      <span className="arch-line" />
      <span className="arch-chevron">↓</span>
      {label ? <span className="arch-connector-label">{label}</span> : null}
    </div>
  )
}

export function ArchitectureFlow({ events = [] }: Props) {
  const inputAction = latestAction(events, 'user_input')
  const retrievedAction = latestAction(events, 'retrieved_context')
  const toolOutAction = latestAction(events, 'tool_output')
  const filterHot =
    retrievedAction === 'drop' || toolOutAction === 'drop'
      ? 'hot-block'
      : retrievedAction === 'allow' || toolOutAction === 'allow'
        ? 'hot-allow'
        : ''

  return (
    <section className="arch" aria-label="System architecture">
      <div className="arch-head">
        <h2>How InjectGuard sits around the model</h2>
        <p>
          The LLM stays in the middle. S1 gates untrusted text on the way in — and again when
          tool results try to re-enter context.
        </p>
      </div>

      <div className="arch-stack">
        <div
          className={`arch-node ${inputAction === 'block' ? 'hot-block' : inputAction === 'allow' ? 'hot-allow' : ''}`}
        >
          <span className="arch-kicker">Operator</span>
          <strong>User message</strong>
        </div>

        <Connector />

        <div
          className={`arch-node gate ${inputAction === 'block' ? 'hot-block' : inputAction === 'allow' ? 'hot-allow' : ''}`}
        >
          <span className="arch-kicker">S1 gate</span>
          <strong>Input classifier</strong>
          <em>block jailbreaks before the agent runs</em>
        </div>

        <Connector />

        <div className="arch-cycle">
          <div className="arch-cycle-col">
            <div className="arch-node model">
              <span className="arch-kicker">Core</span>
              <strong>AI model</strong>
              <em>proposes tools, or writes the reply when done</em>
            </div>

            <Connector label="tool calls" />

            <div className="arch-node">
              <span className="arch-kicker">App code</span>
              <strong>Execute tools</strong>
              <em>reads policies / disputes · writes transfers / refunds</em>
            </div>

            <Connector />

            <div className={`arch-node gate ${filterHot}`}>
              <span className="arch-kicker">S1 filter</span>
              <strong>Retrieved / tool text</strong>
              <em>drop poison, keep a short block notice</em>
            </div>
          </div>

          <div className="arch-return" aria-hidden="true">
            <span>re-enter model</span>
          </div>
        </div>

        <div className="arch-exit">
          <span className="arch-exit-label">no more tools</span>
          <span className="arch-exit-line" aria-hidden="true" />
          <div className="arch-node">
            <span className="arch-kicker">Operator</span>
            <strong>Final reply</strong>
          </div>
        </div>
      </div>

      <ul className="arch-legend">
        <li>
          <span className="swatch gate-swatch" /> S1 Prompt Guard — same classifier, different action
        </li>
        <li>
          <span className="swatch model-swatch" /> Model never executes tools; your app does
        </li>
        <li>
          <span className="swatch drop-swatch" /> Drop = withhold text from the next model turn
        </li>
      </ul>
    </section>
  )
}
