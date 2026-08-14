import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  MessageSquare,
  Activity,
  Database,
  Clock,
  CheckCircle2,
  Wrench,
  ChevronRight,
} from 'lucide-react'
import { useWorkspace } from '../lib/workspace'
import { timeAgo, formatMs, formatNumber, sourceLabel } from '../lib/format'
import { type ToolExecution } from '../lib/api'
import { Skeleton, SourceChip, StatusDot, SectionLabel, EmptyState } from '../lib/ui'
import { cn } from '../lib/utils'

function MetricCell({
  icon: Icon,
  label,
  value,
  valueClassName,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div className="bg-surface px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-faint">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <div className={cn('mt-0.5 text-[15px] font-semibold tabular-nums tracking-tight text-foreground', valueClassName)}>{value}</div>
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const { sources, sessions, analytics, loading } = useWorkspace()
  const [query, setQuery] = useState('')
  const [expandedTool, setExpandedTool] = useState<string | null>(null)

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== 'n' || e.metaKey || e.ctrlKey || e.altKey) return
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      navigate('/chat')
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [navigate])

  const submit = () => {
    const q = query.trim()
    if (!q) return
    navigate(`/chat?q=${encodeURIComponent(q)}`)
  }

  const connectedSources = sources.filter(s => s.status === 'connected')
  const latest = sessions[0]
  const recent = sessions.slice(0, 5)

  const rate = analytics?.tool_success_rate
  const rateLabel = rate == null ? '—' : `${(rate * 100).toFixed(1)}%`
  const medianLabel =
    analytics?.median_tool_latency_ms != null ? formatMs(analytics.median_tool_latency_ms) : '—'

  const executionsFor = useMemo(() => {
    const byTool = new Map<string, ToolExecution[]>()
    for (const ex of analytics?.recent_tool_executions ?? []) {
      const list = byTool.get(ex.tool) ?? []
      list.push(ex)
      byTool.set(ex.tool, list)
    }
    return byTool
  }, [analytics])

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-6xl px-8 py-7">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">Workspace</h1>
            <p className="mt-0.5 text-[12.5px] text-muted">
              Investigate activity across your connected business systems.
            </p>
          </div>
        </div>

        {/* Query composer */}
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-border bg-surface p-1.5 pl-3 transition-colors focus-within:border-primary/50">
          <MessageSquare className="h-4 w-4 shrink-0 text-faint" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            placeholder="Ask a question across your connected systems…"
            className="h-8 w-full bg-transparent text-[13px] text-foreground placeholder:text-faint focus:outline-none"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!query.trim()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-2 text-muted transition-colors hover:border-primary/40 hover:text-primary disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
            aria-label="Ask"
          >
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>

        {/* Connected sources */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <SectionLabel className="mr-1">Connected sources</SectionLabel>
          {loading ? (
            <Skeleton className="h-6 w-72" />
          ) : (
            <>
              {connectedSources.map(s => (
                <SourceChip key={s.integration_type} type={s.integration_type} />
              ))}
              {connectedSources.length === 0 && (
                <span className="text-[11px] text-faint">No sources connected</span>
              )}
              <button
                type="button"
                onClick={() => navigate('/sources')}
                className="text-[11px] font-medium text-faint transition-colors hover:text-muted cursor-pointer"
              >
                Manage connections →
              </button>
            </>
          )}
        </div>

        {/* Last investigation — the core value, end to end */}
        {!loading && latest && (
          <button
            type="button"
            onClick={() => navigate(`/chat/${latest.id}`)}
            className="mt-5 w-full rounded-lg border border-border bg-surface text-left transition-colors hover:border-border-strong cursor-pointer"
          >
            <div className="flex items-center justify-between border-b border-border px-4 py-2">
              <SectionLabel>Last investigation</SectionLabel>
              <span className="text-[10.5px] text-faint">{timeAgo(latest.created_at)}</span>
            </div>
            <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13px] font-medium text-foreground">
                  “{latest.question ?? latest.title ?? 'New conversation'}”
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {(latest.tools ?? []).slice(0, 4).map(t => (
                  <span
                    key={t.tool}
                    className="mono inline-flex items-center gap-1 rounded border border-border bg-surface-2 px-1.5 py-0.5 text-[10.5px] text-muted"
                  >
                    {sourceLabel(t.tool)}
                    <span className="tabular-nums text-foreground">{formatNumber(t.count)}</span>
                  </span>
                ))}
                {(!latest.tools || latest.tools.length === 0) && (
                  <span className="text-[10.5px] text-faint">No tool calls yet</span>
                )}
              </div>
              <div className="flex items-center gap-1 text-[11.5px] text-muted">
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-faint" />
                {latest.result ? (
                  <span className="max-w-[260px] truncate text-foreground">{latest.result}</span>
                ) : (
                  <span>Open investigation</span>
                )}
              </div>
            </div>
          </button>
        )}

        {/* Main grid */}
        <div className="mt-6 grid grid-cols-1 gap-x-8 gap-y-8 lg:grid-cols-[minmax(0,1fr)_300px]">
          {/* Recent investigations */}
          <section>
            <div className="flex items-center justify-between">
              <SectionLabel>Recent investigations</SectionLabel>
              {!loading && sessions.length > 0 && (
                <button
                  type="button"
                  onClick={() => navigate('/activity')}
                  className="text-[11px] font-medium text-muted transition-colors hover:text-foreground cursor-pointer"
                >
                  View all →
                </button>
              )}
            </div>

            {loading ? (
              <div className="mt-3 space-y-2">
                {[0, 1, 2].map(i => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : sessions.length === 0 ? (
              <EmptyState
                icon={MessageSquare}
                title="No conversations yet"
                description="Ask a question to search across your connected systems."
                action={
                  <button
                    type="button"
                    onClick={() => navigate('/chat')}
                    className="text-[12px] font-medium text-muted hover:text-foreground cursor-pointer"
                  >
                    Ask a question →
                  </button>
                }
              />
            ) : (
              <div className="mt-2 divide-y divide-border border-t border-border">
                {recent.map(session => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => navigate(`/chat/${session.id}`)}
                    className="group flex w-full items-center gap-4 rounded-md px-1 py-3 text-left transition-colors hover:bg-surface-2/60 cursor-pointer"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[12.5px] font-medium text-foreground transition-colors group-hover:text-foreground">
                        {session.question ?? session.title ?? 'New conversation'}
                      </div>
                      <div className="mt-1 flex items-center gap-1.5 text-[10.5px] text-faint">
                        {(session.tools ?? []).slice(0, 4).map((t, i) => (
                          <span key={t.tool}>
                            {i > 0 && <span className="mr-1.5 text-border-strong">·</span>}
                            {sourceLabel(t.tool)}
                          </span>
                        ))}
                        {(!session.tools || session.tools.length === 0) && <span>No tool calls</span>}
                      </div>
                    </div>
                    <div className="hidden min-w-0 flex-1 sm:block">
                      {session.result && (
                        <div className="truncate text-[11px] text-muted">{session.result}</div>
                      )}
                    </div>
                    <div className="shrink-0 text-[10.5px] text-faint">{timeAgo(session.created_at)}</div>
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Right rail */}
          <aside className="space-y-6">
            {/* Workspace metrics */}
            <section>
              <SectionLabel>Workspace metrics</SectionLabel>
              <div className="mt-2 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border bg-border">
                <MetricCell icon={Database} label="Investigations" value={loading ? '—' : String(analytics?.investigations ?? 0)} />
                <MetricCell icon={Wrench} label="Tool calls" value={loading ? '—' : String(analytics?.tool_calls ?? 0)} />
                <MetricCell icon={CheckCircle2} label="Success rate" value={loading ? '—' : rateLabel} valueClassName={rate === 1 ? 'text-success' : undefined} />
                <MetricCell icon={Clock} label="Median latency" value={loading ? '—' : medianLabel} />
              </div>
            </section>

            {/* Most used tools */}
            <section>
              <SectionLabel>Most used tools</SectionLabel>
              <div className="mt-2 divide-y divide-border rounded-md border border-border">
                {loading || !analytics || analytics.most_used_tools.length === 0 ? (
                  <div className="px-3 py-3 text-[11px] text-faint">No tool executions yet.</div>
                ) : (
                  analytics.most_used_tools.map(tool => {
                    const executions = executionsFor.get(tool.tool) ?? []
                    const open = expandedTool === tool.tool
                    return (
                      <div key={tool.tool}>
                        <button
                          type="button"
                          onClick={() => setExpandedTool(open ? null : tool.tool)}
                          className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-surface-2/60 cursor-pointer"
                        >
                          <Wrench className="h-3 w-3 shrink-0 text-faint" />
                          <span className="mono min-w-0 flex-1 truncate text-[11px] text-muted">{tool.tool}</span>
                          <span className="tabular-nums text-[11.5px] font-medium text-foreground">
                            {formatNumber(tool.count)}
                          </span>
                          <ChevronRight
                            className={cn('h-3 w-3 shrink-0 text-faint transition-transform', open && 'rotate-90')}
                          />
                        </button>
                        {open && (
                          <div className="space-y-1 border-t border-border px-3 py-2">
                            {executions.map((ex, i) => (
                              <div key={i} className="flex items-center gap-2 text-[10.5px] text-faint">
                                <StatusDot
                                  tone={
                                    ex.status === 'success' ? 'success' : ex.status === 'error' ? 'danger' : 'neutral'
                                  }
                                />
                                <span className="flex-1 capitalize">{ex.status}</span>
                                <span className="tabular-nums">{ex.duration_ms != null ? formatMs(ex.duration_ms) : '—'}</span>
                                <span>{timeAgo(ex.created_at)}</span>
                              </div>
                            ))}
                            {executions.length === 0 && (
                              <div className="text-[10.5px] text-faint">No recent executions recorded.</div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })
                )}
              </div>
            </section>

            {/* Usage */}
            {analytics && analytics.total_tokens > 0 && (
              <section>
                <SectionLabel>Usage</SectionLabel>
                <div className="mt-2 flex items-center justify-between rounded-md border border-border bg-surface px-3 py-2 text-[11px]">
                  <span className="flex items-center gap-1.5 text-muted">
                    <Activity className="h-3 w-3 text-faint" />
                    {formatNumber(analytics.total_tokens)} tokens
                  </span>
                  <span className="tabular-nums text-faint">≈ ${analytics.estimated_cost.toFixed(2)} est.</span>
                </div>
              </section>
            )}
          </aside>
        </div>
      </div>
    </div>
  )
}
