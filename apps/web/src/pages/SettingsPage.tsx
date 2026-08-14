import { useEffect, useState } from 'react'
import { Moon, Sun, Monitor, Cpu, KeyRound, Info, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge, Card, StatusDot, SourceChip } from '../lib/ui'
import { cn } from '../lib/utils'

type Theme = 'dark' | 'light' | 'system'

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    root.classList.toggle('dark', prefersDark)
    root.classList.toggle('light', !prefersDark)
  } else {
    root.classList.toggle('dark', theme === 'dark')
    root.classList.toggle('light', theme === 'light')
  }
}

const THEME_OPTIONS = [
  { value: 'dark' as const, icon: Moon, label: 'Dark' },
  { value: 'light' as const, icon: Sun, label: 'Light' },
  { value: 'system' as const, icon: Monitor, label: 'System' },
]

export default function SettingsPage() {
  const [theme, setTheme] = useState<Theme>('dark')

  useEffect(() => {
    const stored = localStorage.getItem('nexus_theme') as Theme | null
    if (stored) {
      setTheme(stored)
      applyTheme(stored)
    } else {
      applyTheme('dark')
    }
  }, [])

  const selectTheme = (t: Theme) => {
    setTheme(t)
    localStorage.setItem('nexus_theme', t)
    applyTheme(t)
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl px-8 py-7">
        <div className="mb-5">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Settings</h1>
          <p className="mt-0.5 text-[12.5px] text-muted">Platform preferences and connections.</p>
        </div>

        <div className="space-y-4">
          {/* Appearance */}
          <Card className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <span className="text-[13px] font-semibold text-foreground">Appearance</span>
            </div>
            <div className="flex gap-1.5">
              {THEME_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => selectTheme(opt.value)}
                  className={cn(
                    'flex items-center gap-2 rounded-md border px-3 py-1.5 text-[12px] font-medium transition-colors cursor-pointer',
                    theme === opt.value
                      ? 'border-primary/50 bg-primary/10 text-foreground'
                      : 'border-border bg-surface text-muted hover:border-border-strong hover:text-foreground',
                  )}
                >
                  <opt.icon className="h-3.5 w-3.5" />
                  {opt.label}
                </button>
              ))}
            </div>
          </Card>

          {/* LLM Provider */}
          <Card className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <Cpu className="h-3.5 w-3.5 text-muted" />
              <span className="text-[13px] font-semibold text-foreground">LLM Provider</span>
            </div>
            <div className="rounded-md border border-border bg-surface-2/40 px-3.5 py-3">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="text-[12.5px] font-medium text-foreground">
                    OpenRouter · openai/gpt-oss-20b:free
                  </div>
                  <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted">
                    <KeyRound className="h-3 w-3 text-faint" />
                    API key configured on the server
                    <Badge tone="neutral" className="ml-1">••••••••</Badge>
                  </div>
                </div>
                <Badge tone="success">
                  <StatusDot tone="success" />
                  Active
                </Badge>
              </div>
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-faint">
              Provider, model and credentials are managed server-side via environment variables
              (LLM_PROVIDER, LLM_MODEL, OPENROUTER_API_KEY). Settings here reflect the running
              configuration.
            </p>
          </Card>

          {/* Integrations */}
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-semibold text-foreground">Integrations</span>
              </div>
              <Link
                to="/sources"
                className="flex items-center gap-1 text-[11.5px] font-medium text-muted transition-colors hover:text-foreground"
              >
                Manage
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <SourceChip type="github" />
              <SourceChip type="slack" />
              <SourceChip type="hubspot" />
              <SourceChip type="postgres" />
            </div>
          </Card>

          {/* About */}
          <Card className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <Info className="h-3.5 w-3.5 text-muted" />
              <span className="text-[13px] font-semibold text-foreground">About</span>
            </div>
            <div className="space-y-1 text-[12px] text-muted">
              <div className="flex justify-between">
                <span className="text-faint">Product</span>
                <span>Nexus — Enterprise MCP Intelligence Platform</span>
              </div>
              <div className="flex justify-between">
                <span className="text-faint">Version</span>
                <span className="tabular-nums">1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-faint">Stack</span>
                <span>React · FastAPI · MCP</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}