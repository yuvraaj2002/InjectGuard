import { useEffect, useRef, useState } from 'react'
import { classifyMessage } from '../api'
import type { PlaygroundClassifyResponse, PlaygroundOption } from '../api'

const CAUGHT_TYPES = new Set(['direct_override', 'developer_mode', 'dan_persona'])

type Props = {
  hidden: boolean
  active: boolean
  resetKey: number
  options: PlaygroundOption[]
  selectedType: string | null
  onSelect: (type: string) => void
}

function formatPercent(confidence: number) {
  return `${Math.round(confidence * 1000) / 10}%`
}

function parseReason(reason: string) {
  const label = reason.match(/label=(\S+)/)?.[1]
  const score = reason.match(/score=([0-9.]+)/)?.[1]
  return { label, score }
}

function labelMeaning(label: string | undefined, injection: boolean) {
  if (label === 'LABEL_0' || label === 'BENIGN' || label === 'SAFE') return 'Benign'
  if (label === 'LABEL_1' || label === 'MALICIOUS' || label === 'INJECTION' || label === 'JAILBREAK') return 'Injection'
  return injection ? 'Injection' : 'Benign'
}

function prettyToken(value: string) {
  return value.replaceAll('_', ' ')
}

function shortModel(model: string) {
  return model.split('/').pop() || model
}

function Scorecard({ result, turn }: { result: PlaygroundClassifyResponse; turn: number | null }) {
  const flagged = result.injection
  const { label, score } = parseReason(result.reason)
  const meaning = labelMeaning(label, flagged)
  const width = `${Math.max(0, Math.min(100, result.confidence * 100))}%`

  return (
    <article className={flagged ? 'result scorecard caught' : 'result scorecard passed'}>
      {turn !== null && <p className="turn-kicker">Turn {turn}</p>}
      <div className="scorecard-head">
        <div>
          <p className="scorecard-kicker">{flagged ? 'Caught' : 'Missed'}</p>
          <h3>{flagged ? 'Flagged as an injection' : 'Not flagged'}</h3>
          <p>{label ? `Read as ${meaning.toLowerCase()} (${label}).` : `Read as ${meaning.toLowerCase()}.`}</p>
        </div>
        <div className="scorecard-meter">
          <strong>{formatPercent(result.confidence)}</strong>
          <span>confidence</span>
          <div className="meter" role="img" aria-label={`${formatPercent(result.confidence)} confidence`}>
            <span style={{ width }} />
          </div>
        </div>
      </div>
      <dl className="scorecard-facts">
        <div>
          <dt>Label</dt>
          <dd>{label ? `${label} · ${meaning}` : meaning}</dd>
        </div>
        <div>
          <dt>Score</dt>
          <dd>{score ?? result.confidence.toFixed(3)}</dd>
        </div>
        <div>
          <dt>Latency</dt>
          <dd>{Math.round(result.latency_ms)} ms</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{prettyToken(result.source)}</dd>
        </div>
        <div>
          <dt>Sample</dt>
          <dd>{prettyToken(result.type)}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd title={result.model}>{shortModel(result.model)}</dd>
        </div>
      </dl>
    </article>
  )
}

function OptionList({
  options,
  selectedType,
  onSelect,
}: {
  options: PlaygroundOption[]
  selectedType: string | null
  onSelect: (type: string) => void
}) {
  if (options.length === 0) return null
  return (
    <div className="model-grid">
      {options.map((option) => (
        <button
          key={option.type}
          type="button"
          className="model-card"
          aria-pressed={option.type === selectedType}
          onClick={() => onSelect(option.type)}
        >
          <strong>{option.label}</strong>
          <span>{option.description}</span>
        </button>
      ))}
    </div>
  )
}

export function PlaygroundPanel({ hidden, resetKey, options, selectedType, onSelect }: Props) {
  const [results, setResults] = useState<PlaygroundClassifyResponse[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const selected = options.find((option) => option.type === selectedType) ?? null
  const benchRef = useRef<HTMLElement>(null)
  const requestRef = useRef(0)

  useEffect(() => {
    requestRef.current += 1
    setResults(null)
    setError(null)
    setLoading(false)
  }, [resetKey])

  useEffect(() => {
    if (hidden || !selectedType) return
    benchRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [hidden, selectedType, results])

  function choose(type: string) {
    if (type !== selectedType) {
      setResults(null)
      setError(null)
    }
    onSelect(type)
  }

  async function runSelected() {
    if (!selected || loading) return
    const requestId = requestRef.current + 1
    requestRef.current = requestId
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const next = await Promise.all(selected.messages.map((message) => classifyMessage(selected.type, message)))
      if (requestRef.current !== requestId) return
      setResults(next)
    } catch (err) {
      if (requestRef.current !== requestId) return
      setError(err instanceof Error ? err.message : 'Classifier request failed')
    } finally {
      if (requestRef.current === requestId) setLoading(false)
    }
  }

  return (
    <section className="panel playground" hidden={hidden} aria-label="Playground">
      <header className="picker-intro playground-head">
        <h1>Playground</h1>
        <p>Choose a sample, then run it. Only the input classifier scores it. The agent does not run.</p>
      </header>

      {options.length === 0 ? (
        <p className="picker-empty">Jailbreak types appear when the API is online.</p>
      ) : (
        <div className="playground-scroll">
          <section className="picker-group">
            <h2>Caught</h2>
            <OptionList
              options={options.filter((option) => CAUGHT_TYPES.has(option.type))}
              selectedType={selectedType}
              onSelect={choose}
            />
          </section>
          <section className="picker-group">
            <h2>Obfuscated</h2>
            <OptionList
              options={options.filter((option) => !CAUGHT_TYPES.has(option.type))}
              selectedType={selectedType}
              onSelect={choose}
            />
          </section>

          {selected && (
            <section className="specimen" ref={benchRef} aria-live="polite">
              <div className="specimen-verdict">
                <h2>{selected.label}</h2>
                <p className="specimen-note">{selected.description}</p>
              </div>
              <div className="specimen-texts">
                {selected.messages.map((message, index) => (
                  <pre key={`${selected.type}-text-${index}`} className="specimen-sample">
                    {selected.messages.length > 1 ? `Turn ${index + 1}\n${message}` : message}
                  </pre>
                ))}
              </div>
              <button type="button" className="run-classifier" disabled={loading} onClick={() => void runSelected()}>
                {loading ? 'Scoring…' : 'Run classifier'}
              </button>
              {error && <p className="form-error">{error}</p>}
              {results && results.length > 0 && (
                <div className="specimen-response">
                  {results.map((result, index) => (
                    <Scorecard
                      key={`${selected.type}-result-${index}`}
                      result={result}
                      turn={results.length > 1 ? index + 1 : null}
                    />
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      )}
    </section>
  )
}
