import type { AgentPlanView } from '../api'

type Fact = {
  tool?: string
  args?: Record<string, unknown>
  ok?: boolean
  extracted?: unknown
  error?: string
}

function labelize(key: string) {
  return key.replaceAll('_', ' ')
}

function isEmpty(value: unknown): boolean {
  if (value == null || value === '') return true
  if (Array.isArray(value)) return value.length === 0 || value.every(isEmpty)
  if (typeof value === 'object') return Object.values(value as Record<string, unknown>).every(isEmpty)
  return false
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function scalarText(value: unknown) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

function ArgValue({ value }: { value: unknown }) {
  const text = scalarText(value)
  const variable = typeof value === 'string' && text.startsWith('$')
  return <span className={variable ? 'arg-value is-var' : 'arg-value'}>{text}</span>
}

function FieldList({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, value]) => !isEmpty(value))
  if (entries.length === 0) return null
  return (
    <dl className="field-list">
      {entries.map(([key, value]) => (
        <div key={key}>
          <dt>{labelize(key)}</dt>
          <dd>
            <FieldValue value={value} />
          </dd>
        </div>
      ))}
    </dl>
  )
}

function RecordTable({ rows }: { rows: Record<string, unknown>[] }) {
  const keys: string[] = []
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!keys.includes(key) && rows.some((item) => !isEmpty(item[key]))) keys.push(key)
    }
  }
  if (keys.length === 0) return <p className="record-empty">No fields extracted.</p>
  return (
    <div className="table-scroll">
      <table className="fact-table">
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key}>{labelize(key)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {keys.map((key) => (
                <td key={key}>{isEmpty(row[key]) ? '—' : <FieldValue value={row[key]} />}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FieldValue({ value }: { value: unknown }) {
  if (isEmpty(value)) return <span className="record-empty">—</span>
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <ArgValue value={value} />
  }
  if (Array.isArray(value)) {
    if (value.every((item) => typeof item === 'string' || typeof item === 'number')) {
      return (
        <ul className="point-list">
          {value.map((item, index) => (
            <li key={index}>{scalarText(item)}</li>
          ))}
        </ul>
      )
    }
    if (value.every(isRecord)) return <RecordTable rows={value} />
  }
  if (isRecord(value)) return <FieldList data={value} />
  return <span>{scalarText(value)}</span>
}

export function PlanView({ plan }: { plan: AgentPlanView }) {
  const steps = plan.steps ?? []
  const errors = plan.errors ?? []
  return (
    <section className="run-record" aria-label="Plan">
      <header className="run-head">
        <p className="run-kicker">{plan.valid === false ? 'Plan not run' : 'Plan'}</p>
        <h3>{plan.goal || 'Untitled goal'}</h3>
        {plan.notes && <p>{plan.notes}</p>}
      </header>
      {errors.length > 0 && (
        <ul className="plan-errors">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      {steps.length > 0 ? (
        <ol className="plan-steps">
          {steps.map((step, index) => {
            const args = Object.entries(step.args ?? {}).filter(([, value]) => !isEmpty(value))
            return (
              <li key={`${step.tool}-${index}`}>
                <span className="step-index">{index + 1}</span>
                <div>
                  <div className="step-title">
                    <strong>{step.tool}</strong>
                    {step.save_as && <span>saves {step.save_as}</span>}
                  </div>
                  {args.length > 0 && (
                    <div className="arg-row">
                      {args.map(([key, value]) => (
                        <span key={key}>
                          <em>{labelize(key)}</em>
                          <ArgValue value={value} />
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      ) : (
        <p className="record-note">No steps were pinned.</p>
      )}
      {steps.length === 0 && plan.raw_text && <pre className="raw-plan">{plan.raw_text}</pre>}
    </section>
  )
}

export function FactsView({ facts }: { facts: Record<string, unknown>[] }) {
  return (
    <section className="run-record" aria-label="Facts">
      <header className="run-head">
        <p className="run-kicker">Facts</p>
        <h3>What each tool returned</h3>
      </header>
      {facts.map((item, index) => {
        const fact = item as Fact
        const extracted = isRecord(fact.extracted) && !isEmpty(fact.extracted) ? fact.extracted : null
        const args = Object.entries(fact.args ?? {}).filter(([, value]) => !isEmpty(value))
        const showArgs = !extracted && args.length > 0
        const failed = fact.ok === false
        return (
          <article key={`${fact.tool ?? 'step'}-${index}`} className="fact-block">
            <div className="fact-title">
              <strong>{fact.tool || 'Step'}</strong>
              <span className={failed ? 'fact-status bad' : 'fact-status'}>
                {failed ? 'Failed' : extracted ? 'Extracted' : 'Done'}
              </span>
            </div>
            {fact.error && <p className="fact-error">{fact.error}</p>}
            {extracted && <FieldList data={extracted} />}
            {showArgs && (
              <div className="arg-row">
                {args.map(([key, value]) => (
                  <span key={key}>
                    <em>{labelize(key)}</em>
                    <ArgValue value={value} />
                  </span>
                ))}
              </div>
            )}
            {!extracted && !fact.error && fact.ok !== false && !showArgs && (
              <p className="record-note">No extracted fields.</p>
            )}
          </article>
        )
      })}
    </section>
  )
}
