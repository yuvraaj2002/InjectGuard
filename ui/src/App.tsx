import { useEffect, useState } from 'react'
import { fetchHealth, fetchPlaygroundOptions, fetchTools } from './api'
import type { PlaygroundOption, ToolInfo } from './api'
import { ChatPanel } from './components/ChatPanel'
import { LandingPage } from './components/LandingPage'
import { PlaygroundPanel } from './components/PlaygroundPanel'
import './App.css'

type View = 'landing' | 'chat' | 'playground'

function routeFromHash(): View {
  const hash = window.location.hash.slice(1)
  if (hash === 'chat' || hash === 'playground') return hash
  return 'landing'
}

function App() {
  const [view, setView] = useState<View>(routeFromHash)
  const [tools, setTools] = useState<ToolInfo[]>([])
  const [options, setOptions] = useState<PlaygroundOption[]>([])
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [usedTools, setUsedTools] = useState<string[]>([])
  const [model, setModel] = useState('')
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [theme, setTheme] = useState<'light' | 'night'>('light')
  const [resetKey, setResetKey] = useState(0)

  useEffect(() => {
    const saved = window.localStorage.getItem('injectguard-theme')
    const next = saved === 'night' ? 'night' : 'light'
    setTheme(next)
    document.documentElement.dataset.theme = next === 'night' ? 'night' : 'light'
  }, [])

  function toggleTheme() {
    const next = theme === 'night' ? 'light' : 'night'
    setTheme(next)
    document.documentElement.dataset.theme = next
    window.localStorage.setItem('injectguard-theme', next)
  }

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        const [ok, toolsResponse, playgroundOptions] = await Promise.all([
          fetchHealth(),
          fetchTools(),
          fetchPlaygroundOptions(),
        ])
        if (cancelled) return
        setHealthy(ok)
        setTools(toolsResponse.tools)
        setModel(toolsResponse.model)
        setOptions(playgroundOptions)
      } catch (err) {
        if (cancelled) return
        setHealthy(false)
        setBootError(err instanceof Error ? err.message : 'Failed to reach the API')
      }
    }
    void boot()
    return () => {
      cancelled = true
    }
  }, [])

  const used = new Set(usedTools)

  function clearScreen() {
    setSelectedType(null)
    setUsedTools([])
    setResetKey((key) => key + 1)
  }

  useEffect(() => {
    const sync = () => setView(routeFromHash())
    window.addEventListener('hashchange', sync)
    window.addEventListener('popstate', sync)
    return () => {
      window.removeEventListener('hashchange', sync)
      window.removeEventListener('popstate', sync)
    }
  }, [])

  function openView(next: View) {
    const url = next === 'landing' ? window.location.pathname + window.location.search : `#${next}`
    window.history.pushState(null, '', url)
    setView(next)
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
  }

  if (view === 'landing') {
    return <LandingPage theme={theme} onToggleTheme={toggleTheme} onEnter={openView} />
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <button type="button" className="brand" onClick={() => openView('landing')}>
          <img src="/injectguard-logo.jpg" alt="" width={32} height={32} />
          <span className="brand-name">
            <em>Inject</em>Guard
          </span>
        </button>
        <nav className="view-switch" aria-label="Sections">
          <button type="button" aria-current={view === 'chat' ? 'page' : undefined} onClick={() => openView('chat')}>
            Chat
          </button>
          <button type="button" aria-current={view === 'playground' ? 'page' : undefined} onClick={() => openView('playground')}>
            Playground
          </button>
        </nav>

        {view === 'chat' && (
          <div className="side-scroll">
            <p className="side-label">Available tools</p>
            {tools.length === 0 ? (
              <p className="side-empty">{bootError ?? 'Tools appear when the API is online.'}</p>
            ) : (
              <ul className="side-list">
                {tools.map((tool) => (
                  <li key={tool.name} className={used.has(tool.name) ? 'tool-row used' : 'tool-row'}>
                    <span className="tool-dot" aria-hidden="true" />
                    <div>
                      <strong>{tool.name}</strong>
                      <p>{tool.description}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="sidebar-foot">
          <span className="status">
            <span className={healthy ? 'status-dot on' : healthy === false ? 'status-dot off' : 'status-dot'} />
            <em>{healthy === null ? 'Connecting' : healthy ? model || 'Online' : 'Offline'}</em>
          </span>
          <button type="button" className="ghost" onClick={toggleTheme}>
            {theme === 'night' ? 'Light' : 'Dark'}
          </button>
        </div>
      </aside>

      <main>
        <div className="main-bar">
          <button type="button" className="clear-screen" onClick={() => openView('landing')}>
            Index
          </button>
          <button type="button" className="clear-screen" onClick={clearScreen}>
            Clear
          </button>
        </div>
        <ChatPanel hidden={view !== 'chat'} resetKey={resetKey} onUsedTools={setUsedTools} onModel={setModel} />
        <PlaygroundPanel
          hidden={view !== 'playground'}
          active={view === 'playground'}
          resetKey={resetKey}
          options={options}
          selectedType={selectedType}
          onSelect={setSelectedType}
        />
      </main>
    </div>
  )
}

export default App
