import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { fetchHealth, fetchTools, sendChat } from './api'
import type { ChatResponse, ToolInfo } from './api'
import './App.css'

const EXAMPLES = [
  'List the open support tickets.',
  'How do I reset my password?',
  'Read ticket-002 and summarize the issue.',
  'List my recent emails.',
  "Create a ticket titled 'Laptop cannot join VPN' in project it with severity P3 and summary 'VPN profile missing after reimage.'",
]

function App() {
  const [query, setQuery] = useState('List the open support tickets.')
  const [tools, setTools] = useState<ToolInfo[]>([])
  const [model, setModel] = useState('…')
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ChatResponse | null>(null)

  useEffect(() => {
    let cancelled = false

    async function boot() {
      try {
        const [ok, toolsResponse] = await Promise.all([fetchHealth(), fetchTools()])
        if (cancelled) return
        setHealthy(ok)
        setTools(toolsResponse.tools)
        setModel(toolsResponse.model)
      } catch (err) {
        if (cancelled) return
        setHealthy(false)
        setError(err instanceof Error ? err.message : 'Failed to load tools')
      }
    }

    void boot()
    return () => {
      cancelled = true
    }
  }, [])

  const usedToolNames = useMemo(() => {
    return new Set(result?.tool_calls.map((call) => call.name) ?? [])
  }, [result])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const message = query.trim()
    if (!message || loading) return

    setLoading(true)
    setError(null)

    try {
      const response = await sendChat(message)
      setResult(response)
      setModel(response.model)
      setHealthy(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="shell">
      <header className="hero">
        <motion.h1
          className="brand"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          InjectGuard
        </motion.h1>
        <motion.p
          className="tagline"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.05 }}
        >
          Watch OpsPilot choose tools in real time — query in, tool calls out,
          vulnerable baseline on purpose.
        </motion.p>
        <div className="meta-row">
          <span className={`pill ${healthy ? 'ok' : healthy === false ? 'bad' : ''}`}>
            API {healthy === null ? 'checking…' : healthy ? 'online' : 'offline'}
          </span>
          <span className="pill">
            model <strong>{model}</strong>
          </span>
          <span className="pill">
            tools <strong>{tools.length}</strong>
          </span>
        </div>
      </header>

      <div className="layout">
        <aside className="panel">
          <div className="panel-header">
            <h2>Available tools</h2>
            <span>what the model can call</span>
          </div>
          <div className="tools-list">
            {tools.map((tool, index) => (
              <motion.article
                key={tool.name}
                className={`tool-card ${usedToolNames.has(tool.name) ? 'used' : ''}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.04 * index }}
              >
                <h3>{tool.name}</h3>
                <p>{tool.description}</p>
              </motion.article>
            ))}
            {tools.length === 0 && (
              <p className="empty">Start the FastAPI server to load tools.</p>
            )}
          </div>
        </aside>

        <div className="main-stack">
          <form className="panel composer" onSubmit={onSubmit}>
            <label htmlFor="query">Ask OpsPilot</label>
            <textarea
              id="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask about docs, emails, or tickets…"
            />
            <div className="composer-actions">
              <button className="btn btn-primary" type="submit" disabled={loading}>
                {loading ? 'Running…' : 'Send query'}
              </button>
              <button
                className="btn btn-ghost"
                type="button"
                onClick={() => {
                  setResult(null)
                  setError(null)
                }}
              >
                Clear result
              </button>
            </div>
            <div className="examples">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="chip"
                  onClick={() => setQuery(example)}
                >
                  {example}
                </button>
              ))}
            </div>
            {error && <div className="error">{error}</div>}
          </form>

          <section className="panel answer">
            <h2>Model reply</h2>
            {result ? (
              <p className="answer-body">{result.reply}</p>
            ) : (
              <p className="empty">
                Send a query to see the final answer. Tool choices appear below.
              </p>
            )}
          </section>

          <section className="panel trace">
            <h2>Tool trace</h2>
            <AnimatePresence mode="wait">
              {result && result.tool_calls.length > 0 ? (
                <motion.div
                  key="trace"
                  className="trace-list"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  {result.tool_calls.map((call, index) => (
                    <motion.article
                      key={`${call.round}-${call.name}-${index}`}
                      className="trace-card"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <div className="trace-top">
                        <code>{call.name}</code>
                        <span className="round">round {call.round}</span>
                      </div>
                      <div className="trace-grid">
                        <div className="trace-block">
                          <h4>Input</h4>
                          <pre>{JSON.stringify(call.arguments, null, 2)}</pre>
                        </div>
                        <div className="trace-block">
                          <h4>Output</h4>
                          <pre>{call.output}</pre>
                        </div>
                      </div>
                    </motion.article>
                  ))}
                </motion.div>
              ) : (
                <motion.p
                  key="empty-trace"
                  className="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  {result
                    ? 'The model answered without calling a tool.'
                    : 'Each chosen tool will show its arguments and raw output here.'}
                </motion.p>
              )}
            </AnimatePresence>
          </section>
        </div>
      </div>
    </div>
  )
}

export default App
