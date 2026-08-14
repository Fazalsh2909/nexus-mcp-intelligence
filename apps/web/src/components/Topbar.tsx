import { useLocation, useNavigate } from 'react-router-dom'
import { Search, ShieldCheck } from 'lucide-react'
import { useWorkspace } from '../lib/workspace'
import { connectedCount } from '../lib/workspace'
import { StatusDot, Kbd } from '../lib/ui'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Workspace',
  '/chat': 'Chat',
  '/activity': 'Activity',
  '/sources': 'Sources',
  '/connections': 'Connections',
  '/evaluations': 'Evaluations',
  '/settings': 'Settings',
}

export function Topbar({ onOpenPalette }: { onOpenPalette: () => void }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { sources, loading, user } = useWorkspace()

  const total = sources.length || 4
  const connected = connectedCount(sources)
  const allHealthy = total > 0 && connected === total

  const title = location.pathname.startsWith('/chat/')
    ? 'Chat'
    : (PAGE_TITLES[location.pathname] ?? 'Workspace')

  return (
    <header className="flex h-11 shrink-0 items-center gap-4 border-b border-border bg-background px-4">
      {/* Breadcrumb */}
      <div className="flex min-w-0 items-center gap-1.5 text-[12.5px]">
        <span className="text-faint">Workspace</span>
        <span className="text-faint">/</span>
        <span className="font-medium text-foreground">{title}</span>
      </div>

      <div className="ml-auto flex items-center gap-2">
        {/* Connection health */}
        <button
          type="button"
          onClick={() => navigate('/sources')}
          title={allHealthy ? 'All sources connected' : `${connected}/${total} sources connected`}
          className="flex h-7 items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-[11.5px] font-medium text-muted transition-colors hover:border-border-strong hover:text-foreground cursor-pointer"
        >
          <StatusDot tone={loading ? 'neutral' : allHealthy ? 'success' : 'warning'} />
          {loading ? 'Checking…' : allHealthy ? 'All systems operational' : `${connected}/${total} connected`}
        </button>

        {/* Search */}
        <button
          type="button"
          onClick={onOpenPalette}
          className="flex h-7 items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-[11.5px] text-muted transition-colors hover:border-border-strong hover:text-foreground cursor-pointer"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden lg:inline">Search</span>
          <Kbd>⌘K</Kbd>
        </button>

        {/* User */}
        <div
          className="flex h-7 items-center gap-2 rounded-md border border-border bg-surface pl-1 pr-2.5"
          title={user?.email ?? ''}
        >
          <div className="flex h-[18px] w-[18px] items-center justify-center rounded bg-surface-2 border border-border text-[9px] font-semibold text-muted">
            {user ? user.name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase() : '—'}
          </div>
          <span className="text-[11.5px] font-medium text-muted hidden md:inline">{user?.name ?? '…'}</span>
          <ShieldCheck className="h-3 w-3 text-faint" />
        </div>
      </div>
    </header>
  )
}