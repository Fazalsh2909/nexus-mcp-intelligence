import { markLoggedOut } from './auth'

const API_BASE = '/api/v1'

export interface ToolActivity {
  tool: string
  status: 'running' | 'success' | 'error'
  description: string
  duration_ms?: number
}

export interface SourceRef {
  type: string
  url: string
  title: string
  detail?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceRef[]
  toolActivities?: ToolActivity[]
  created_at?: string
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  message_count?: number
  question?: string
  tools?: Array<{ tool: string; count: number }>
  result?: string
}

export interface ToolExecution {
  tool: string
  status: string
  duration_ms?: number
  created_at: string
}

export interface ConfirmationRequest {
  action_id: string
  tool: string
  description: string
  arguments: Record<string, unknown>
}

export interface Analytics {
  total_queries: number
  successful_queries: number
  failed_queries: number
  avg_latency_ms: number
  avg_tool_calls_per_query: number
  total_tokens: number
  estimated_cost: number
  most_used_tools: Array<{ tool: string; count: number }>
  investigations: number
  tool_calls: number
  tool_success_rate: number | null
  median_tool_latency_ms: number | null
  recent_tool_executions: ToolExecution[]
}

function handleUnauthorized(status: number) {
  if (status === 401 && localStorage.getItem('nexus_token')) {
    localStorage.removeItem('nexus_token')
    markLoggedOut()
    if (window.location.pathname !== '/login') {
      window.location.assign('/login')
    }
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('nexus_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  handleUnauthorized(res.status)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }))
    const err = new Error(error.detail || `HTTP ${res.status}`) as Error & { status?: number }
    err.status = res.status
    throw err
  }
  return res.json()
}

async function* stream(path: string, body: Record<string, unknown>) {
  const token = localStorage.getItem('nexus_token')
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })

  handleUnauthorized(res.status)
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }))
    const err = new Error(error.detail || `HTTP ${res.status}`) as Error & { status?: number }
    err.status = res.status
    throw err
  }

  const reader = res.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value)
    const lines = text.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6))
          yield event
        } catch {
          // ignore malformed SSE events
        }
      }
    }
  }
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, name: string, password: string) =>
      request<{ id: string; email: string; name: string }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, name, password }),
      }),
    me: () => request<{ id: string; email: string; name: string }>('/auth/me'),
  },
  sources: {
    list: () => request<Array<{ id: string; integration_type: string; status: string }>>('/sources/'),
    connect: (type: string) =>
      request<{ status: string; authorize_url?: string }>(`/sources/${type}/connect`, { method: 'POST' }),
    disconnect: (type: string) => request<{ status: string }>(`/sources/${type}/disconnect`, { method: 'POST' }),
    test: (type: string) => request<{ status: string }>(`/sources/${type}/test`, { method: 'POST' }),
  },
  chat: {
    sessions: () => request<ChatSession[]>('/chat/sessions'),
    create: (title?: string) =>
      request<{ id: string; title: string }>('/chat/sessions', {
        method: 'POST',
        body: JSON.stringify({ title }),
      }),
    get: (id: string) =>
      request<{
        id: string
        title: string
        messages: Array<{
          id: string
          role: string
          content: string
          sources?: SourceRef[]
          tool_calls?: ToolActivity[]
          created_at: string
        }>
      }>(`/chat/sessions/${id}`),
    rename: (id: string, title: string) =>
      request<ChatSession>(`/chat/sessions/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title }),
      }),
    send: async function* (sessionId: string, content: string) {
      yield* stream(`/chat/sessions/${sessionId}/messages`, { content })
    },
    confirm: async function* (sessionId: string, actionId: string) {
      yield* stream(`/chat/sessions/${sessionId}/actions/${actionId}/confirm`, {})
    },
    cancel: (sessionId: string, actionId: string) =>
      request<{ status: string; action_id: string }>(
        `/chat/sessions/${sessionId}/actions/${actionId}/cancel`,
        { method: 'POST' },
      ),
  },
  analytics: {
    get: () => request<Analytics>('/analytics/'),
  },
  evaluations: {
    list: () => request<{ evaluations: Array<Record<string, unknown>>; message: string }>('/evaluations/'),
    run: () =>
      request<{ status: string; message: string }>('/evaluations/run', {
        method: 'POST',
      }),
  },
  meta: {
    health: async () => {
      const res = await fetch('/health')
      return (await res.json()) as { status: string; service: string }
    },
  },
}
