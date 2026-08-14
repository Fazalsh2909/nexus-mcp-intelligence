import { NavLink } from 'react-router-dom'
import {
  Zap,
  LayoutGrid,
  MessageSquare,
  Activity,
  Database,
  GitCompareArrows,
  Settings,
  Plus,
  Globe,
  LogOut,
  Wrench,
} from 'lucide-react'
import { useWorkspace } from '../lib/workspace'
import { chatTarget } from '../lib/sessionCache'
import { SourceIcon, SectionLabel } from '../lib/ui'
import { cn } from '../lib/utils'

const NAV_GROUPS: Array<{ label: string; items: Array<{ to: string; label: string; icon: React.ComponentType<{ className?: string }>; lastSession?: boolean }> }> = [
  {
    label: 'Workspace',
    items: [
      { to: '/', label: 'Workspace', icon: LayoutGrid },
      { to: '/chat', label: 'Chat', icon: MessageSquare, lastSession: true },
      { to: '/activity', label: 'Activity', icon: Activity },
      { to: '/sources', label: 'Sources', icon: Database },
      { to: '/evaluations', label: 'Evaluations', icon: GitCompareArrows },
    ],
  },
  {
    label: 'Management',
    items: [
      { to: '/connections', label: 'Connections', icon: Globe },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
]

function NavItem({
  to,
  label,
  icon: Icon,
  lastSession,
}: {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  lastSession?: boolean
}) {
  const target = lastSession ? chatTarget() : to
  const isLastChatActive = lastSession && target !== '/chat'
  return (
    <NavLink
      to={target}
      end={!isLastChatActive}
      className={({ isActive }) =>
        cn(
          'group relative flex items-center gap-2.5 h-[30px] px-2.5 rounded-md text-[13px] transition-colors',
          isActive
            ? 'bg-selected text-foreground font-medium'
            : 'text-muted hover:text-foreground hover:bg-hover',
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 h-3.5 w-[2px] rounded-full bg-primary" />
          )}
          <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-foreground' : 'text-faint group-hover:text-muted')} />
          <span className="truncate">{label}</span>
        </>
      )}
    </NavLink>
  )
}

export function AppSidebar({ onLogout }: { onLogout: () => void }) {
  const { user, loading } = useWorkspace()
  const sourceTypes = ['github', 'slack', 'hubspot', 'postgres']

  return (
    <aside className="flex h-full w-[240px] shrink-0 flex-col border-r border-border bg-sidebar">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-3 pt-3.5 pb-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-surface-2">
          <Zap className="h-3.5 w-3.5 text-primary" />
        </div>
        <div className="min-w-0 leading-tight">
          <div className="text-[13px] font-semibold tracking-tight text-foreground">Nexus</div>
        </div>
      </div>

      {/* New conversation */}
      <div className="px-2.5 pb-2">
        <NavLink
          to="/chat"
          className="flex h-[30px] items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-[12.5px] font-medium text-foreground transition-colors hover:border-border-strong hover:bg-surface-2"
        >
          <Plus className="h-3.5 w-3.5 text-muted" />
          New conversation
          <span className="ml-auto text-[10.5px] text-faint">N</span>
        </NavLink>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto no-scrollbar px-2.5 pb-3 pt-1">
        {NAV_GROUPS.map(group => (
          <div key={group.label} className="mb-4">
            <SectionLabel className="px-2.5 mb-1.5">{group.label}</SectionLabel>
            <div className="space-y-px">
              {group.items.map(item => (
                <NavItem key={item.to} {...item} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-3 pt-2.5 pb-2.5 space-y-2.5">
        {!loading && (
          <>
            {/* Workspace */}
            <div className="flex items-center gap-2">
              <div className="flex h-[22px] w-[22px] items-center justify-center rounded border border-border bg-surface">
                <Wrench className="h-3 w-3 text-muted" />
              </div>
              <div className="min-w-0 flex-1 leading-tight">
                <div className="flex items-center gap-1.5 text-[12px] font-medium text-foreground truncate">
                  Nexus Workspace
                </div>
                <div className="text-[10.5px] text-faint">Workspace</div>
              </div>
            </div>

            {/* Connected sources */}
            <div>
              <SectionLabel className="mb-1">Connected sources</SectionLabel>
              <div className="space-y-1">
                {sourceTypes.map(type => {
                  return (
                    <div key={type} className="flex items-center gap-2 px-0.5">
                      <SourceIcon type={type} className="h-3 w-3 text-faint" />
                      <span className="text-[11.5px] capitalize text-muted flex-1">
                        {type === 'postgres' ? 'PostgreSQL' : type}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}

        {/* User */}
        <div className="flex items-center gap-2 border-t border-border pt-2.5">
          <div className="flex h-[26px] w-[26px] items-center justify-center rounded-md bg-surface-2 border border-border text-[10.5px] font-semibold text-muted">
            {user ? user.name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase() : '—'}
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <div className="text-[12px] font-medium text-foreground truncate">{user?.name ?? '…'}</div>
            <div className="text-[10.5px] text-faint truncate">{user?.email ?? ''}</div>
          </div>
          <button
            type="button"
            onClick={onLogout}
            title="Sign out"
            className="flex h-6 w-6 items-center justify-center rounded-md text-faint transition-colors hover:bg-surface-2 hover:text-foreground cursor-pointer"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </aside>
  )
}