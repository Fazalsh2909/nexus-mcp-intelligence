import { useState } from 'react'
import { ChevronRight, MessageSquare, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useWorkspace } from '../lib/workspace'
import { Badge, EmptyState, Input, SourceIcon } from '../lib/ui'
import { timeAgo, formatClock, formatDateTime } from '../lib/format'

function dayLabel(createdAt: string): string {
  const created = new Date(createdAt).setHours(0, 0, 0, 0)
  const today = new Date().setHours(0, 0, 0, 0)
  const diff = Math.round((today - created) / 86_400_000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  if (diff < 7) return 'This week'
  if (diff < 30) return 'This month'
  return 'Older'
}

const DAY_ORDER = ['Today', 'Yesterday', 'This week', 'This month', 'Older']

export default function ActivityPage() {
  const { sessions, loading } = useWorkspace()
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const filtered = sessions.filter(s =>
    s.title.toLowerCase().includes(query.toLowerCase()),
  )

  const groups = new Map<string, typeof filtered>()
  for (const session of filtered) {
    const label = dayLabel(session.created_at)
    if (!groups.has(label)) groups.set(label, [])
    groups.get(label)!.push(session)
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-4xl px-8 py-7">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Activity</h1>
            <p className="mt-0.5 text-[12.5px] text-muted">
              Every conversation run through Nexus, newest first.
            </p>
          </div>
          <Badge tone="neutral">{sessions.length} conversations</Badge>
        </div>

        <div className="relative mb-4 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          <Input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Filter conversations…"
            className="pl-8"
          />
        </div>

        {loading ? (
          <div className="space-y-4">
            {[0, 1, 2].map(i => (
              <div key={i} className="h-14 animate-pulse rounded-lg border border-border bg-surface-2/40" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={MessageSquare}
            title={query ? 'No matching conversations' : 'No activity yet'}
            description={
              query
                ? 'Try a different filter.'
                : 'Questions asked from the Workspace will appear here.'
            }
          />
        ) : (
          <div className="space-y-6">
            {DAY_ORDER.filter(d => groups.has(d)).map(label => (
              <div key={label}>
                <div className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-faint">
                  {label}
                </div>
                <div className="overflow-hidden rounded-lg border border-border bg-surface">
                  {groups.get(label)!.map((session, i) => (
                    <button
                      key={session.id}
                      type="button"
                      onClick={() => navigate(`/chat/${session.id}`)}
                      className={
                        'flex w-full items-center gap-3.5 px-4 py-2.5 text-left transition-colors hover:bg-surface-2/50 cursor-pointer ' +
                        (i > 0 ? 'border-t border-border/60 ' : '')
                      }
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-2">
                        <MessageSquare className="h-3.5 w-3.5 text-muted" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[13px] font-medium text-foreground">{session.title}</div>
                        <div className="mt-0.5 flex items-center gap-2 text-[11px] text-faint">
                          <span>{formatDateTime(session.created_at)}</span>
                          <span>·</span>
                          <span>{timeAgo(session.created_at)}</span>
                          <span className="hidden items-center gap-1 sm:flex">
                            <span>·</span>
                            <span className="flex items-center gap-1 text-faint">
                              <SourceIcon type="mcp" className="h-3 w-3" />
                              MCP agents
                            </span>
                          </span>
                        </div>
                      </div>
                      <span className="shrink-0 text-[10.5px] tabular-nums text-faint">{formatClock(session.created_at)}</span>
                      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-faint" />
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}