export type ToolInfo = {
  name: string
  description: string
  parameters: Record<string, unknown>
}

export type GuardLayerInfo = {
  id: string
  label: string
  enabled: boolean
  description: string
}

export type ToolCallTrace = {
  round: number
  name: string
  arguments: Record<string, unknown>
  output: string
}

export type GuardEventTrace = {
  layer: 'user_input' | 'retrieved_context' | 'tool_output'
  action: 'allow' | 'block' | 'drop'
  injection: boolean
  confidence: number
  reason: string
  tool_name?: string | null
}

export type AgentPlanView = {
  valid?: boolean
  errors?: string[]
  goal?: string
  steps?: { tool: string; args?: Record<string, unknown>; save_as?: string | null }[]
  notes?: string | null
  raw_text?: string
}

export type ChatResponse = {
  message: string
  reply: string
  model: string
  available_tools: string[]
  tool_calls: ToolCallTrace[]
  guard_events: GuardEventTrace[]
  plan?: AgentPlanView | null
  facts?: Record<string, unknown>[]
  blocked: boolean
}

export type ToolsResponse = {
  model: string
  tools: ToolInfo[]
  decision_model: string
  guard_layers: GuardLayerInfo[]
}

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') return data.detail
    return JSON.stringify(data)
  } catch {
    return response.statusText || 'Request failed'
  }
}

export async function fetchHealth(): Promise<boolean> {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) return false
  const data = await response.json()
  return data.status === 'ok'
}

export async function fetchTools(): Promise<ToolsResponse> {
  const response = await fetch(`${API_BASE}/tools`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json()
}

export type ChatStreamEvent = {
  type: string
  text?: string
  reply?: string
  blocked?: boolean
  detail?: string
  model?: string
  tool_calls?: ToolCallTrace[]
  plan?: AgentPlanView | null
  facts?: Record<string, unknown>[]
}

export async function streamChat(
  message: string,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ message }),
    signal,
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  if (!response.body) {
    throw new Error('Chat stream returned no body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let sawDone = false

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''
    for (const chunk of chunks) {
      const data = chunk
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (!data) continue
      const event = JSON.parse(data) as ChatStreamEvent
      if (event.type === 'error') {
        throw new Error(event.detail || 'Chat stream failed')
      }
      if (event.type === 'done') sawDone = true
      onEvent(event)
    }
  }

  if (!sawDone) {
    throw new Error('The stream ended before a reply')
  }
}

export async function sendChat(message: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json()
}

export type PlaygroundOption = {
  type: string
  label: string
  description: string
  messages: string[]
}

export type PlaygroundClassifyResponse = {
  type: string
  message: string
  injection: boolean
  confidence: number
  reason: string
  model: string
  source: string
  latency_ms: number
}

export async function fetchPlaygroundOptions(): Promise<PlaygroundOption[]> {
  const response = await fetch(`${API_BASE}/playground/options`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  const data = await response.json()
  return data.options ?? []
}

export async function classifyMessage(
  type: string,
  message: string,
): Promise<PlaygroundClassifyResponse> {
  const response = await fetch(`${API_BASE}/playground/classify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, message }),
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json()
}
