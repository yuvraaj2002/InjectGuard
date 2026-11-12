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
