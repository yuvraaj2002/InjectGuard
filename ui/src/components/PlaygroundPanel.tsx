import { useCallback, useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { classifyMessage } from '../api'
import type { PlaygroundClassifyResponse, PlaygroundOption } from '../api'

type Run = {
  id: string
  label: string
  results: PlaygroundClassifyResponse[]
}

const CAUGHT_TYPES = new Set(['direct_override', 'developer_mode', 'dan_persona'])

type Props = {
  hidden: boolean
  active: boolean
  options: PlaygroundOption[]
  selectedType: string | null
  onSelect: (type: string) => void
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M8 13V3.5M8 3.5 4.25 7.25M8 3.5l3.75 3.75"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function formatPercent(confidence: number) {
  return `${Math.round(confidence * 1000) / 10}%`
}

function pastedText(option: PlaygroundOption) {
  if (option.messages.length === 1) return option.messages[0]
  return option.messages.map((message, index) => `Turn ${index + 1}\n${message}`).join('\n\n')
}

function OptionCards({
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

export function PlaygroundPanel({ hidden, active, options, selectedType, onSelect }: Props) {
  const [runs, setRuns] = useState<Run[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const threadRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const selected = options.find((option) => option.type === selectedType) ?? null

  useEffect(() => {
    setDraft(selected ? pastedText(selected) : '')
  }, [selected])

  useEffect(() => {
    const input = inputRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(input.scrollHeight, 220)}px`
  }, [draft])

  useEffect(() => {
    const node = threadRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [runs, loading, selectedType])

  const run = useCallback(async () => {
    if (!selected || loading) return
    const messages = selected.messages.length === 1 ? [draft.trim()] : selected.messages
    if (messages.some((message) => !message)) return
    setLoading(true)
    setError(null)
    try {
      const results = await Promise.all(
        messages.map((message) => classifyMessage(selected.type, message)),
      )
      setRuns((prev) => [...prev, { id: `${selected.type}-${Date.now()}`, label: selected.label, results }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Classifier request failed')
    } finally {
      setLoading(false)
    }
  }, [draft, loading, selected])

  useEffect(() => {
    if (!active) return
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key !== 'Enter' || event.shiftKey || event.metaKey || event.ctrlKey || event.altKey) return
      const target = event.target
      if (
        (target instanceof HTMLTextAreaElement || target instanceof HTMLInputElement) &&
        target.offsetParent !== null
      ) {
        return
      }
      event.preventDefault()
      void run()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active, run])

  return (
    <section className="panel" hidden={hidden} aria-label="Playground">
      <div className={runs.length === 0 ? 'thread thread-stage' : 'thread'} ref={threadRef}>
        <div className="picker">
          <header className="picker-intro">
            <h1>Playground</h1>
            <p>Pick a jailbreak. The sample goes in the message field, then press Enter.</p>
          </header>
          {options.length === 0 ? (
            <p className="picker-empty">Jailbreak types appear when the API is online.</p>
          ) : (
            <>
              <section className="picker-group">
                <h2>Caught</h2>
                <OptionCards
                  options={options.filter((option) => CAUGHT_TYPES.has(option.type))}
                  selectedType={selectedType}
                  onSelect={onSelect}
                />
              </section>
              <section className="picker-group">
                <h2>Obfuscated</h2>
                <OptionCards
                  options={options.filter((option) => !CAUGHT_TYPES.has(option.type))}
                  selectedType={selectedType}
                  onSelect={onSelect}
                />
              </section>
            </>
          )}
        </div>
        {runs.length > 0 && (
          <div className="thread-inner playground-results">
            {runs.map((item) => (
              <article key={item.id}>
                <p className="run-label">{item.label}</p>
                {item.results.map((result, index) => {
                  const passed = !result.injection
                  return (
                    <div key={`${item.id}-${index}`} className={passed ? 'result passed' : 'result caught'}>
                      <div className="result-status">
                        {item.results.length > 1 && <span className="turn-kicker">Turn {index + 1}</span>}
                        <span className="result-dot" aria-hidden="true" />
                        <div>
                          <strong>{passed ? 'Passed through' : 'Did not pass through'}</strong>
                          <p>
                            {passed ? 'The classifier did not flag this.' : 'The classifier flagged this as an injection.'}{' '}
                            {Math.round(result.latency_ms)} ms
                          </p>
                        </div>
                        <span className="result-score">{formatPercent(result.confidence)}</span>
                      </div>
                    </div>
                  )
                })}
              </article>
            ))}
            {loading && (
              <p className="run-label" aria-live="polite">
                Checking the input classifier…
              </p>
            )}
          </div>
        )}
      </div>

      <div className="dock playground-dock">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            void run()
          }}
        >
          <div className="composer">
            <textarea
              ref={inputRef}
              className="pasted"
              rows={1}
              value={draft}
              placeholder="Select a jailbreak type"
              aria-label="Jailbreak message"
              disabled={!selected || loading}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event: KeyboardEvent<HTMLTextAreaElement>) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void run()
                }
              }}
            />
            <button className="send" type="submit" disabled={!selected || loading || !draft.trim()} aria-label="Run classifier">
              <SendIcon />
            </button>
          </div>
        </form>
        {error ? (
          <p className="form-error">{error}</p>
        ) : (
          <p className="hint">{selected ? 'Enter to run this sample through the input classifier' : 'Choose a card, then press Enter'}</p>
        )}
      </div>
    </section>
  )
}
