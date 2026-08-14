import * as React from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search,
  LayoutGrid,
  MessageSquare,
  Activity,
  Database,
  GitCompareArrows,
  Settings,
  Globe,
  Plus,
  CornerDownLeft,
  FileText,
} from 'lucide-react'
import { useWorkspace } from '../lib/workspace'
import { chatTarget } from '../lib/sessionCache'
import { timeAgo } from '../lib/format'
import { cn } from '../lib/utils'

interface Entry {
  id: string
  label: string
  hint?: string
  icon: React.ComponentType<{ className?: string }>
  onSelect: () => void
}

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const navigate = useNavigate()
  const { sessions } = useWorkspace()
  const [query, setQuery] = React.useState('')
  const [active, setActive] = React.useState(0)
  const inputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    if (open) {
      setQuery('')
      setActive(0)
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open])

  const baseEntries: Entry[] = [
    { id: 'nav-home', label: 'Open Intelligence', icon: LayoutGrid, onSelect: () => navigate('/') },
    { id: 'nav-chat', label: 'Open Chat', icon: MessageSquare, onSelect: () => navigate(chatTarget()) },
    { id: 'nav-activity', label: 'Open Activity', icon: Activity, onSelect: () => navigate('/activity') },
    { id: 'nav-sources', label: 'Open Sources', icon: Database, onSelect: () => navigate('/sources') },
    { id: 'nav-evals', label: 'Open Evaluations', icon: GitCompareArrows, onSelect: () => navigate('/evaluations') },
    { id: 'nav-conn', label: 'Open Connections', icon: Globe, onSelect: () => navigate('/connections') },
    { id: 'nav-settings', label: 'Open Settings', icon: Settings, onSelect: () => navigate('/settings') },
    { id: 'act-new', label: 'New conversation', hint: 'N', icon: Plus, onSelect: () => navigate('/chat') },
  ]

  const conversationEntries: Entry[] = sessions
    .slice(0, 12)
    .map(s => ({
      id: `conv-${s.id}`,
      label: s.title || 'Untitled conversation',
      hint: timeAgo(s.created_at),
      icon: FileText,
      onSelect: () => navigate(`/chat/${s.id}`),
    }))

  const q = query.trim().toLowerCase()
  const filteredBase = baseEntries.filter(e => e.label.toLowerCase().includes(q))
  const filteredConvs = conversationEntries.filter(e => e.label.toLowerCase().includes(q))

  const groups: Array<{ label: string; entries: Entry[] }> = []
  if (filteredBase.length > 0) groups.push({ label: 'Navigate & actions', entries: filteredBase })
  if (filteredConvs.length > 0) groups.push({ label: 'Conversations', entries: filteredConvs })

  const all = groups.flatMap(g => g.entries)

  const run = (index: number) => {
    const entry = all[index]
    if (!entry) return
    onOpenChange(false)
    entry.onSelect()
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive(a => Math.min(a + 1, all.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive(a => Math.max(a - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      run(active)
    } else if (e.key === 'Escape') {
      onOpenChange(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60" />
        <Dialog.Content
          onKeyDown={onKeyDown}
          className="fixed left-1/2 top-[18vh] z-50 w-[min(92vw,560px)] -translate-x-1/2"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.98, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="overflow-hidden rounded-lg border border-border-strong bg-surface shadow-2xl shadow-black/40"
          >
            {/* Input */}
            <div className="flex items-center gap-2.5 border-b border-border px-3.5">
              <Search className="h-4 w-4 shrink-0 text-faint" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => {
                  setQuery(e.target.value)
                  setActive(0)
                }}
                placeholder="Search conversations, tools, pages…"
                className="h-11 w-full bg-transparent text-[13px] text-foreground placeholder:text-faint focus:outline-none"
              />
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="flex h-5 w-5 items-center justify-center rounded text-faint transition-colors hover:bg-surface-2 hover:text-muted cursor-pointer"
                  aria-label="Close"
                >
                  <span className="text-[11px] font-medium">esc</span>
                </button>
              </Dialog.Close>
            </div>

            {/* Results */}
            <div className="max-h-[320px] overflow-y-auto scrollbar-thin py-1.5">
              {groups.length === 0 && (
                <div className="px-4 py-8 text-center text-xs text-faint">
                  No results for “{query}”
                </div>
              )}

              {groups.map(group => (
                <div key={group.label} className="mb-1">
                  <div className="px-3.5 pb-1 pt-2 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-faint">
                    {group.label}
                  </div>
                  {group.entries.map(entry => {
                    const idx = all.indexOf(entry)
                    const isActive = idx === active
                    return (
                      <button
                        key={entry.id}
                        type="button"
                        onMouseEnter={() => setActive(idx)}
                        onClick={() => run(idx)}
                        className={cn(
                          'flex w-full items-center gap-2.5 px-3.5 py-2 text-left text-[13px] transition-colors cursor-pointer',
                          isActive ? 'bg-surface-2 text-foreground' : 'text-muted',
                        )}
                      >
                        <entry.icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-foreground' : 'text-faint')} />
                        <span className="flex-1 truncate">{entry.label}</span>
                        {entry.hint && <span className="shrink-0 text-[11px] text-faint">{entry.hint}</span>}
                        {isActive && <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-faint" />}
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="flex items-center gap-3 border-t border-border bg-surface-2/50 px-3.5 py-2 text-[10.5px] text-faint">
              <span className="flex items-center gap-1">
                <kbd className="kbd">↑</kbd>
                <kbd className="kbd">↓</kbd> navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="kbd">↵</kbd> select
              </span>
              <span className="ml-auto">Nexus command palette</span>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}