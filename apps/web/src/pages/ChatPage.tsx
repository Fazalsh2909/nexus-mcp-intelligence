import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Send,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  FileText,
  ExternalLink,
  XCircle,
  Layers,
  CircleDot,
  Pencil,
  ShieldAlert,
  Check,
  Ban,
} from 'lucide-react'
import { api, type ChatMessage, type ToolActivity, type SourceRef, type ConfirmationRequest } from '../lib/api'
import { timeAgo, formatMs, sourceLabel } from '../lib/format'
import { Button, StatusDot, SectionLabel, SourceIcon, SourceChip, Kbd } from '../lib/ui'
import { useWorkspace } from '../lib/workspace'
import {
  getCachedConversation,
  setCachedConversation,
  isStreamingSession,
  markStreaming,
  markStreamComplete,
} from '../lib/sessionCache'
import { Markdown } from '../lib/Markdown'
import { cn } from '../lib/utils'

const SUGGESTED_QUESTIONS = [
  'Search Slack for recent messages about deployments',
  'Which tables exist in PostgreSQL?',
  'List contacts in HubSpot',
  'Search GitHub issues for open bugs',
]

function useAutoResizeTextarea(minHeight: number, maxHeight: number) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const adjustHeight = useCallback(
    (reset?: boolean) => {
      const textarea = textareaRef.current
      if (!textarea) return
      if (reset) {
        textarea.style.height = `${minHeight}px`
        return
      }
      textarea.style.height = `${minHeight}px`
      const newHeight = Math.max(minHeight, Math.min(textarea.scrollHeight, maxHeight))
      textarea.style.height = `${newHeight}px`
    },
    [minHeight, maxHeight],
  )

  useEffect(() => {
    const handleResize = () => adjustHeight()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [adjustHeight])

  return { textareaRef, adjustHeight }
}

function ToolStep({ activity, index }: { activity: ToolActivity; index: number }) {
  const tone: 'success' | 'warning' | 'danger' = activity.status === 'success' ? 'success' : activity.status === 'error' ? 'danger' : 'warning'
  return (
    <div className="flex items-start gap-2.5 px-3.5 py-2">
      <StatusDot tone={tone} pulse={activity.status === 'running'} className="mt-1.5" />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="mono text-[11.5px] text-foreground">{activity.tool}</span>
          <span className="text-[10.5px] text-faint capitalize">
            {activity.status === 'running' ? 'Running' : activity.status === 'success' ? 'Success' : 'Failed'}
          </span>
          {activity.duration_ms !== undefined && (
            <span className="ml-auto shrink-0 text-[10.5px] tabular-nums text-faint">
              {formatMs(activity.duration_ms)}
            </span>
          )}
        </div>
        {activity.description && (
          <div className="mt-0.5 truncate text-[11px] text-muted">{activity.description}</div>
        )}
      </div>
      <span className="mt-0.5 shrink-0 text-[10px] tabular-nums text-faint">#{index + 1}</span>
    </div>
  )
}

function CitationChip({ type, title, url, detail }: { type: string; title: string; url: string; detail?: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="group inline-flex max-w-[220px] items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 text-[11px] text-muted transition-colors hover:border-primary/40 hover:text-foreground"
    >
      <SourceIcon type={type} className="h-3 w-3 shrink-0 text-faint" />
      <span className="truncate">{title}</span>
      <span className="shrink-0 text-faint">·</span>
      <span className="shrink-0 capitalize text-faint group-hover:text-foreground">{type}</span>
      {detail && <span className="hidden shrink-0 text-faint">— {detail}</span>}
      <ExternalLink className="h-3 w-3 shrink-0 text-faint" />
    </a>
  )
}

function AssistantMessage({ msg, streaming }: { msg: ChatMessage; streaming: boolean }) {
  const isError = msg.content.startsWith('Error')
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div className="group flex gap-3">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-border bg-surface-2">
        <Layers className="h-3 w-3 text-muted" />
      </div>
      <div className="min-w-0 flex-1 space-y-2.5">
        <div className="flex items-center gap-2">
          <span className="text-[11.5px] font-semibold text-foreground">Nexus</span>
          {msg.created_at && <span className="text-[10.5px] text-faint">{timeAgo(msg.created_at)}</span>}
        </div>

        {isError ? (
          <div className="rounded-md border border-danger/25 bg-danger/5 px-3 py-2.5">
            <div className="flex items-center gap-2 text-[12.5px] text-danger">
              <XCircle className="h-3.5 w-3.5" />
              {msg.content.replace(/^Error:\s*/, '')}
            </div>
            <button
              type="button"
              onClick={() => setShowDetails(v => !v)}
              className="mt-1.5 flex items-center gap-1 text-[11px] text-muted transition-colors hover:text-foreground cursor-pointer"
            >
              <ChevronRight className={cn('h-3 w-3 transition-transform', showDetails && 'rotate-90')} />
              Technical details
            </button>
            {showDetails && (
              <div className="mono mt-2 overflow-x-auto rounded border border-border bg-background px-2.5 py-2 text-[11px] text-muted">
                {msg.content}
              </div>
            )}
          </div>
        ) : (
          <>
            <Markdown>{msg.content}</Markdown>
            {streaming && (
              <span className="streaming-cursor mt-1 inline-block h-3.5 w-[2px] bg-primary" />
            )}
          </>
        )}

        {msg.sources && msg.sources.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-faint">Sources</div>
            <div className="flex flex-wrap gap-1.5">
              {msg.sources.map((s, i) => (
                <CitationChip key={`${s.url}-${i}`} {...s} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function UserMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex justify-end gap-3">
      <div className="max-w-[75%] rounded-md border border-border bg-surface-2 px-3.5 py-2 text-[13px] leading-relaxed text-foreground">
        {msg.content}
      </div>
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-border bg-surface">
        <span className="text-[9px] font-semibold text-muted">YOU</span>
      </div>
    </div>
  )
}

function ConfirmationCard({
  pending,
  busy,
  onConfirm,
  onCancel,
}: {
  pending: ConfirmationRequest
  busy: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="rounded-md border border-warning/30 bg-warning/5 px-3.5 py-3">
      <div className="flex items-center gap-2 text-[12.5px] font-medium text-foreground">
        <ShieldAlert className="h-4 w-4 text-warning" />
        This action needs your confirmation
      </div>
      <div className="mt-1.5 space-y-1 text-[12px] text-muted">
        <div className="mono text-[11px] text-foreground">{pending.tool}</div>
        <div>{pending.description}</div>
        <div className="mono overflow-x-auto rounded border border-border bg-background px-2 py-1.5 text-[11px] text-faint">
          {JSON.stringify(pending.arguments)}
        </div>
      </div>
      <div className="mt-2.5 flex gap-2">
        <Button size="sm" variant="primary" onClick={onConfirm} disabled={busy} className="gap-1.5">
          <Check className="h-3.5 w-3.5" />
          Confirm
        </Button>
        <Button size="sm" variant="secondary" onClick={onCancel} disabled={busy} className="gap-1.5">
          <Ban className="h-3.5 w-3.5" />
          Decline
        </Button>
      </div>
    </div>
  )
}

export default function ChatPage() {
  const { id: sessionId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { sessions: workspaceSessions, refresh } = useWorkspace()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [toolActivities, setToolActivities] = useState<ToolActivity[]>([])
  const [showExecution, setShowExecution] = useState(false)
  const [showLeft, setShowLeft] = useState(true)
  const [showRight, setShowRight] = useState(true)
  const [historyNote, setHistoryNote] = useState('')
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const [pendingAction, setPendingAction] = useState<ConfirmationRequest | null>(null)
  const [isConfirming, setIsConfirming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sentRef = useRef(false)
  const assistantIdRef = useRef<string | null>(null)
  const stateRef = useRef({ messages, toolActivities })
  stateRef.current = { messages, toolActivities }
  const streamSessionRef = useRef<string | null>(null)
  const { textareaRef, adjustHeight } = useAutoResizeTextarea(24, 140)

  const currentTitle = workspaceSessions.find(s => s.id === sessionId)?.title ?? 'New conversation'

  // Persist the last active conversation so the sidebar "Chat" link can return to it
  useEffect(() => {
    if (sessionId) localStorage.setItem('nexus_last_session', sessionId)
  }, [sessionId])

  useEffect(() => {
    if (messages.length === 0 && toolActivities.length === 0) return
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, toolActivities])

  // Load conversation history when a session is selected; cached copies render
  // instantly so navigating back never shows a blank conversation.
  useEffect(() => {
    const prevId = sessionId
    return () => {
      if (prevId) setCachedConversation(prevId, stateRef.current)
    }
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) {
      setMessages([])
      setToolActivities([])
      setHistoryNote('')
      setPendingAction(null)
      return
    }
    let cancelled = false
    const cached = getCachedConversation(sessionId)
    setMessages(cached?.messages ?? [])
    setToolActivities(cached?.toolActivities ?? [])
    setHistoryNote(cached ? '' : '')

    const applyLoaded = (data: {
      messages?: Array<{
        id: string
        role: string
        content: string
        sources?: SourceRef[]
        tool_calls?: ToolActivity[]
        created_at: string
      }>
    }) => {
      if (cancelled || streamSessionRef.current === sessionId) return
      const loaded: ChatMessage[] = (data.messages ?? []).map(m => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        sources: m.sources ?? undefined,
        toolActivities: m.tool_calls ?? undefined,
        created_at: m.created_at,
      }))
      setMessages(loaded)
      const loadedLast = [...loaded].reverse().find(m => m.role === 'assistant')
      setCachedConversation(sessionId, {
        messages: loaded,
        toolActivities: loadedLast?.toolActivities ?? [],
      })
    }

    api.chat
      .get(sessionId)
      .then(applyLoaded)
      .catch(err => {
        if (err && (err as { status?: number }).status === 404) {
          localStorage.removeItem('nexus_last_session')
          if (!cancelled) navigate('/chat', { replace: true })
          return
        }
        if (!cancelled && !cached) {
          setHistoryNote('Conversation history is unavailable — starting a fresh session.')
        }
      })

    // A stream may have been running for this session when we left the page.
    // Keep polling until it completes so the answer doesn't appear frozen.
    let poll: ReturnType<typeof setInterval> | null = null
    if (isStreamingSession(sessionId)) {
      poll = setInterval(() => {
        const stillStreaming = isStreamingSession(sessionId)
        api.chat
          .get(sessionId)
          .then(data => {
            applyLoaded(data)
            if (!stillStreaming && poll) {
              clearInterval(poll)
              // The stream finished; fetch once more to catch its final flush.
              setTimeout(() => {
                if (cancelled) return
                api.chat.get(sessionId).then(applyLoaded).catch(() => {})
              }, 1500)
            }
          })
          .catch(() => {})
      }, 2000)
    }

    return () => {
      cancelled = true
      if (poll) clearInterval(poll)
    }
  }, [sessionId])

  // Auto-send query passed from the home page (?q=)
  useEffect(() => {
    if (sentRef.current) return
    const q = searchParams.get('q')
    if (q) {
      sentRef.current = true
      sendMessage(q)
    }
  }, [sessionId, searchParams])

  const sendMessage = async (content: string) => {
    if (!content.trim() || isStreaming || pendingAction) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: content.trim(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    adjustHeight(true)
    setIsStreaming(true)
    setThinking(false)
    assistantIdRef.current = null
    setToolActivities([])
    setShowExecution(true)

    let currentSessionId = sessionId
    const currentToolActivities: ToolActivity[] = []

    try {
      if (!currentSessionId) {
        const created = await api.chat.create('New conversation')
        currentSessionId = created.id
        refresh()
        navigate(`/chat/${created.id}`, { replace: true })
      }
      streamSessionRef.current = currentSessionId
      markStreaming(currentSessionId)

      let assistantContent = ''

      for await (const event of api.chat.send(currentSessionId, content)) {
        if (event.type === 'thinking') {
          setThinking(true)
        } else if (event.type === 'tool_start') {
          setThinking(false)
          const activity: ToolActivity = {
            tool: event.tool,
            status: 'running',
            description: event.description,
          }
          currentToolActivities.push(activity)
          setToolActivities([...currentToolActivities])
        } else if (event.type === 'tool_result') {
          const idx = currentToolActivities.findIndex(a => a.tool === event.tool && a.status === 'running')
          if (idx >= 0) {
            currentToolActivities[idx].status = 'success'
            currentToolActivities[idx].duration_ms = event.duration_ms
          }
          setToolActivities([...currentToolActivities])
        } else if (event.type === 'tool_error') {
          const idx = currentToolActivities.findIndex(a => a.tool === event.tool && a.status === 'running')
          if (idx >= 0) {
            currentToolActivities[idx].status = 'error'
          }
          setToolActivities([...currentToolActivities])
        } else if (event.type === 'token') {
          setThinking(false)
          assistantContent += event.content
          if (!assistantIdRef.current) {
            assistantIdRef.current = `assistant-${Date.now()}`
          }
          const aid = assistantIdRef.current
          setMessages(prev => {
            const existing = prev.find(m => m.id === aid)
            if (existing) {
              return prev.map(m => (m.id === aid ? { ...m, content: assistantContent } : m))
            }
            return [...prev, { id: aid, role: 'assistant', content: assistantContent }]
          })
        } else if (event.type === 'confirmation_request') {
          setThinking(false)
          setPendingAction(event)
        } else if (event.type === 'sources') {
          const aid = assistantIdRef.current
          if (aid) {
            setMessages(prev => prev.map(m => (m.id === aid ? { ...m, sources: event.sources } : m)))
          }
        } else if (event.type === 'error') {
          assistantContent = `Error: ${event.content}`
          setMessages(prev => [
            ...prev,
            { id: `error-${Date.now()}`, role: 'assistant', content: assistantContent },
          ])
        }
      }
    } catch (err) {
      if (err && (err as { status?: number }).status === 404) {
        localStorage.removeItem('nexus_last_session')
        setMessages(prev => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: 'Error: Session not found — starting a new conversation.',
          },
        ])
        navigate('/chat', { replace: true })
        return
      }
      setMessages(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Failed to send message'}`,
        },
      ])
    } finally {
      setIsStreaming(false)
      setThinking(false)
      streamSessionRef.current = null
      if (currentSessionId) {
        markStreamComplete(currentSessionId)
      }
      setToolActivities(currentToolActivities)
      refresh()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleConfirm = async () => {
    if (!sessionId || !pendingAction || isConfirming) return
    setIsConfirming(true)
    const currentSessionId = sessionId
    const currentToolActivities: ToolActivity[] = []
    assistantIdRef.current = null
    let assistantContent = ''

    try {
      for await (const event of api.chat.confirm(currentSessionId, pendingAction.action_id)) {
        if (event.type === 'thinking') {
          setThinking(true)
        } else if (event.type === 'tool_start') {
          setThinking(false)
          currentToolActivities.push({
            tool: event.tool,
            status: 'running',
            description: event.description,
          })
          setToolActivities([...currentToolActivities])
        } else if (event.type === 'tool_result') {
          const idx = currentToolActivities.findIndex(a => a.tool === event.tool && a.status === 'running')
          if (idx >= 0) {
            currentToolActivities[idx].status = 'success'
            currentToolActivities[idx].duration_ms = event.duration_ms
          }
          setToolActivities([...currentToolActivities])
        } else if (event.type === 'tool_error') {
          const idx = currentToolActivities.findIndex(a => a.tool === event.tool && a.status === 'running')
          if (idx >= 0) {
            currentToolActivities[idx].status = 'error'
          }
          setToolActivities([...currentToolActivities])
        } else if (event.type === 'token') {
          setThinking(false)
          assistantContent += event.content
          if (!assistantIdRef.current) {
            assistantIdRef.current = `assistant-${Date.now()}`
          }
          const aid = assistantIdRef.current
          setMessages(prev => {
            const existing = prev.find(m => m.id === aid)
            if (existing) {
              return prev.map(m => (m.id === aid ? { ...m, content: assistantContent } : m))
            }
            return [...prev, { id: aid, role: 'assistant', content: assistantContent }]
          })
        } else if (event.type === 'sources') {
          const aid = assistantIdRef.current
          if (aid) {
            setMessages(prev => prev.map(m => (m.id === aid ? { ...m, sources: event.sources } : m)))
          }
        } else if (event.type === 'error') {
          setMessages(prev => [
            ...prev,
            { id: `error-${Date.now()}`, role: 'assistant', content: `Error: ${event.content}` },
          ])
        }
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Failed to confirm action'}`,
        },
      ])
    } finally {
      setIsConfirming(false)
      setPendingAction(null)
      setThinking(false)
      setToolActivities(currentToolActivities)
      refresh()
    }
  }

  const handleCancel = async () => {
    if (!sessionId || !pendingAction || isConfirming) return
    setIsConfirming(true)
    try {
      await api.chat.cancel(sessionId, pendingAction.action_id)
      setMessages(prev => [
        ...prev,
        {
          id: `cancel-${Date.now()}`,
          role: 'assistant',
          content: 'The action was declined and nothing was changed.',
        },
      ])
    } catch {
      // keep the card visible if the request failed
    } finally {
      setIsConfirming(false)
      setPendingAction(null)
    }
  }

  const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')

  const saveTitle = async () => {
    const next = titleDraft.trim()
    if (!sessionId || !next) {
      setEditingTitle(false)
      return
    }
    try {
      await api.chat.rename(sessionId, next)
      refresh()
    } catch {
      // rename failed; keep the previous title
    }
    setEditingTitle(false)
  }
  const sourcesUsed = lastAssistant?.sources ?? []
  const executionSources = toolActivities.length > 0 ? toolActivities : (lastAssistant?.toolActivities ?? [])
  const completed = executionSources.filter(a => a.status !== 'running')
  const totalDuration = completed.reduce((acc, a) => acc + (a.duration_ms ?? 0), 0)
  const hasMessages = messages.length > 0

  const sourceCounts = new Map<string, number>()
  for (const a of executionSources) {
    const label = sourceLabel(a.tool)
    sourceCounts.set(label, (sourceCounts.get(label) ?? 0) + 1)
  }

  return (
    <div className="flex min-h-0 flex-1">
      {/* Left: conversations */}
      {showLeft && (
        <aside className="flex w-[250px] shrink-0 flex-col border-r border-border bg-sidebar">
          <div className="flex items-center justify-between px-3 pt-2.5 pb-2">
            <SectionLabel>Conversations</SectionLabel>
            <button
              type="button"
              onClick={() => {
                setMessages([])
                setToolActivities([])
                navigate('/chat')
              }}
              title="New conversation (N)"
              className="flex h-6 w-6 items-center justify-center rounded-md border border-border text-muted transition-colors hover:border-border-strong hover:text-foreground cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-2">
            {workspaceSessions.length === 0 ? (
              <div className="px-2 py-8 text-center text-[11.5px] text-faint">No conversations yet</div>
            ) : (
              <div className="space-y-px">
                {workspaceSessions.map(session => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => navigate(`/chat/${session.id}`)}
                    className={cn(
                      'flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left transition-colors cursor-pointer',
                      session.id === sessionId ? 'bg-surface-2' : 'hover:bg-surface-2/60',
                    )}
                  >
                    <FileText className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', session.id === sessionId ? 'text-foreground' : 'text-faint')} />
                    <div className="min-w-0 flex-1">
                      <div className={cn('truncate text-[12px]', session.id === sessionId ? 'font-medium text-foreground' : 'text-muted')}>
                        {session.title}
                      </div>
                      <div className="text-[10px] text-faint">{timeAgo(session.created_at)}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="border-t border-border px-3 py-2 text-[10.5px] text-faint">
            <Kbd>N</Kbd> new conversation
          </div>
        </aside>
      )}

      {/* Center: conversation */}
      <section className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <div className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
          <button
            type="button"
            onClick={() => setShowLeft(v => !v)}
            title="Toggle conversations"
            className="flex h-[26px] w-[26px] items-center justify-center rounded-md text-faint transition-colors hover:bg-surface-2 hover:text-foreground cursor-pointer"
          >
            {showLeft ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
          </button>
          <div className="group min-w-0 flex-1">
            {sessionId && editingTitle ? (
              <input
                autoFocus
                value={titleDraft}
                onChange={e => setTitleDraft(e.target.value)}
                onBlur={saveTitle}
                onKeyDown={e => {
                  if (e.key === 'Enter') saveTitle()
                  if (e.key === 'Escape') setEditingTitle(false)
                }}
                className="w-full max-w-[320px] rounded border border-primary/50 bg-surface px-1.5 py-0.5 text-[12.5px] font-medium text-foreground focus:outline-none"
              />
            ) : (
              <div className="flex items-center gap-1.5">
                <div className="truncate text-[12.5px] font-medium text-foreground">{currentTitle}</div>
                {sessionId && (
                  <button
                    type="button"
                    title="Rename conversation"
                    onClick={() => {
                      setTitleDraft(currentTitle === 'New conversation' ? '' : currentTitle)
                      setEditingTitle(true)
                    }}
                    className="hidden h-5 w-5 shrink-0 items-center justify-center rounded text-faint transition-colors hover:bg-surface-2 hover:text-foreground group-hover:flex cursor-pointer"
                  >
                    <Pencil className="h-3 w-3" />
                  </button>
                )}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => setShowExecution(v => !v)}
            disabled={toolActivities.length === 0}
            className={cn(
              'flex h-[26px] items-center gap-1.5 rounded-md px-2 text-[11px] font-medium transition-colors cursor-pointer disabled:opacity-40 disabled:pointer-events-none',
              showExecution ? 'bg-surface-2 text-foreground' : 'text-muted hover:bg-surface-2/60 hover:text-foreground',
            )}
          >
            <CircleDot className="h-3 w-3" />
            Execution
            {toolActivities.length > 0 && (
              <span className="tabular-nums text-faint">{toolActivities.length}</span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setShowRight(v => !v)}
            title="Toggle context panel"
            className="flex h-[26px] w-[26px] items-center justify-center rounded-md text-faint transition-colors hover:bg-surface-2 hover:text-foreground cursor-pointer"
          >
            {showRight ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
          </button>
        </div>

        {/* Execution strip */}
        {showExecution && executionSources.length > 0 && (
          <div className="shrink-0 border-b border-border bg-surface-2/40">
            <div className="flex items-center gap-2 px-3.5 py-1.5">
              <SectionLabel className="text-[10px]">Execution</SectionLabel>
              <span className="ml-auto text-[10.5px] text-faint">
                {isStreaming
                  ? 'Running…'
                  : `${completed.length} call${completed.length === 1 ? '' : 's'} · ${formatMs(totalDuration)}`}
              </span>
            </div>
            <div className="divide-y divide-border/60 pb-1">
              {executionSources.map((a, i) => (
                <ToolStep key={`${a.tool}-${i}`} activity={a} index={i} />
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="mx-auto max-w-3xl px-6 py-5">
            {historyNote && (
              <div className="mb-3 rounded-md border border-warning/25 bg-warning/5 px-3 py-2 text-[11.5px] text-warning">
                {historyNote}
              </div>
            )}

            {!hasMessages && !isStreaming && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface-2">
                  <Layers className="h-4 w-4 text-muted" />
                </div>
                <h2 className="text-[15px] font-semibold text-foreground">Ask a question</h2>
                <p className="mt-1 max-w-sm text-xs leading-relaxed text-muted">
                  Search across Slack, GitHub, HubSpot and PostgreSQL.
                </p>
                <div className="mt-5 grid w-full max-w-md grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {SUGGESTED_QUESTIONS.map(q => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => {
                        setInput(q)
                        textareaRef.current?.focus()
                      }}
                      className="rounded-md border border-border bg-surface px-3 py-2 text-left text-[11.5px] text-muted transition-colors hover:border-primary/40 hover:text-foreground cursor-pointer"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-5">
              {messages.map(msg =>
                msg.role === 'user' ? (
                  <UserMessage key={msg.id} msg={msg} />
                ) : (
                  <AssistantMessage
                    key={msg.id}
                    msg={msg}
                    streaming={isStreaming && msg.id === lastAssistant?.id}
                  />
                ),
              )}
            </div>

            {pendingAction && (
              <div className="mb-4">
                <ConfirmationCard
                  pending={pendingAction}
                  busy={isConfirming}
                  onConfirm={handleConfirm}
                  onCancel={handleCancel}
                />
              </div>
            )}

            {thinking && (
              <div className="mt-5 flex items-center gap-2 text-[12px] text-muted">
                <StatusDot tone="warning" pulse />
                Working…
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Composer */}
        <div className="shrink-0 border-t border-border bg-background px-4 pb-3 pt-2.5">
          <div className="mx-auto max-w-3xl">
            <div className="flex items-end gap-2 rounded-lg border border-border bg-surface p-2 transition-colors focus-within:border-primary/50">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => {
                  setInput(e.target.value)
                  adjustHeight()
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ask Nexus across your connected systems…"
                rows={1}
                className="max-h-[140px] min-h-[24px] flex-1 resize-none bg-transparent px-2 py-1 text-[13px] text-foreground placeholder:text-faint focus:outline-none"
                style={{ overflow: 'hidden' }}
              />
              <Button
                size="md"
                variant="secondary"
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isStreaming || !!pendingAction || isConfirming}
                className="h-8 w-9 border-border px-0 text-muted hover:border-primary/40 hover:text-primary"
                aria-label="Send"
              >
                <Send className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="mt-1.5 flex items-center justify-between px-1">
              <span className="text-[10.5px] text-faint">
                {pendingAction ? 'Confirm or decline the action above to continue' : 'Enter to send · Shift+Enter for newline'}
              </span>
              {isStreaming && toolActivities.length > 0 && (
                <span className="flex items-center gap-1.5 text-[10.5px] text-muted">
                  <StatusDot tone="warning" pulse />
                  {toolActivities[toolActivities.length - 1].description || toolActivities[toolActivities.length - 1].tool}
                </span>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Right: context */}
      {showRight && (
        <aside className="flex w-[270px] shrink-0 flex-col border-l border-border bg-background">
          <div className="flex items-center justify-between px-3.5 pt-2.5 pb-2">
            <SectionLabel>Context</SectionLabel>
            {isStreaming && <StatusDot tone="warning" pulse />}
          </div>
          <div className="flex-1 overflow-y-auto scrollbar-thin px-3.5 pb-3 space-y-5">
            {/* Sources used */}
            <div>
              <div className="mb-1.5 text-[11px] font-medium text-muted">Sources used</div>
              {sourcesUsed.length === 0 && executionSources.length === 0 ? (
                <p className="text-[11.5px] leading-relaxed text-faint">
                  Sources consulted by Nexus appear here after a query runs.
                </p>
              ) : (
                <div className="space-y-1.5">
                  {sourcesUsed.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {sourcesUsed.map((s, i) => (
                        <SourceChip key={i} type={s.type} className="normal-case" />
                      ))}
                    </div>
                  )}
                  {[...sourceCounts.entries()].map(([label, count]) => (
                    <div key={label} className="flex items-center justify-between rounded-md border border-border bg-surface px-2.5 py-1.5">
                      <div className="flex items-center gap-2">
                        <SourceIcon type={label} className="h-3 w-3 text-faint" />
                        <span className="text-[11.5px] text-muted">{label}</span>
                      </div>
                      <span className="text-[11px] tabular-nums text-faint">
                        {count} call{count === 1 ? '' : 's'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Execution summary */}
            <div>
              <div className="mb-1.5 text-[11px] font-medium text-muted">Execution</div>
              {executionSources.length === 0 ? (
                <p className="text-[11.5px] leading-relaxed text-faint">
                  Tool execution metadata is recorded for every query.
                </p>
              ) : (
                <div className="overflow-hidden rounded-md border border-border">
                  {executionSources.map((a, i) => (
                    <div
                      key={`${a.tool}-${i}`}
                      className={cn(
                        'flex items-center gap-2 px-2.5 py-1.5',
                        i > 0 && 'border-t border-border/60',
                      )}
                    >
                      <StatusDot tone={a.status === 'success' ? 'success' : a.status === 'error' ? 'danger' : 'warning'} pulse={a.status === 'running'} />
                      <span className="mono flex-1 truncate text-[11px] text-foreground">{a.tool}</span>
                      <span className="text-[10px] tabular-nums text-faint">
                        {a.status === 'running' ? '…' : formatMs(a.duration_ms)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Session */}
            <div>
              <div className="mb-1.5 text-[11px] font-medium text-muted">Session</div>
              <div className="space-y-1 text-[11.5px] text-faint">
                <div className="flex justify-between">
                  <span>Status</span>
                  <span className="flex items-center gap-1.5 text-muted">
                    <StatusDot tone={isStreaming ? 'warning' : 'success'} pulse={isStreaming} />
                    {isStreaming ? 'Streaming' : 'Idle'}
                  </span>
                </div>
                {sessionId && (
                  <div className="flex justify-between">
                    <span>ID</span>
                    <span className="mono text-muted">{sessionId.slice(0, 8)}</span>
                  </div>
                )}
                {messages.length > 0 && (
                  <div className="flex justify-between">
                    <span>Messages</span>
                    <span className="tabular-nums text-muted">{messages.length}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          {executionSources.length > 0 && (
            <div className="border-t border-border px-3.5 py-2.5">
              <div className="text-[11px] text-faint">
                {completed.length}/{executionSources.length} calls succeeded
                {totalDuration > 0 && ` · ${formatMs(totalDuration)} total`}
              </div>
            </div>
          )}
        </aside>
      )}
    </div>
  )
}