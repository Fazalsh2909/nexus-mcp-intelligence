import { useEffect, useState } from 'react'
import {
  ChevronRight,
  ChevronDown,
  RefreshCw,
  PlugZap,
  Plug,
  TestTube,
  CheckCircle2,
  ShieldCheck,
  Clock,
} from 'lucide-react'
import { api } from '../lib/api'
import { Badge, Button, SourceIcon, StatusDot, SectionLabel } from '../lib/ui'
import { cn } from '../lib/utils'
import { timeAgo } from '../lib/format'

interface Connection {
  id: string
  integration_type: string
  status: string
}

const INTEGRATIONS = [
  {
    type: 'github',
    label: 'GitHub',
    description: 'Search issues, repositories and code',
    capabilities: ['Search issues', 'List repositories', 'Get issue details', 'Search code', 'Create issues'],
  },
  {
    type: 'slack',
    label: 'Slack',
    description: 'Search messages and threads',
    capabilities: ['Search messages', 'Get threads', 'List channels', 'Get channel history'],
  },
  {
    type: 'hubspot',
    label: 'HubSpot',
    description: 'Search contacts, companies and deals',
    capabilities: ['Search contacts', 'Get contacts', 'Search companies', 'Search deals'],
  },
  {
    type: 'postgres',
    label: 'PostgreSQL',
    description: 'Query database tables (read-only)',
    capabilities: ['List tables', 'Describe tables', 'Run read-only queries', 'Count rows'],
  },
]

function DetailPanel({
  integration,
  status,
  lastTested,
  testing,
  onTest,
  onClose,
}: {
  integration: (typeof INTEGRATIONS)[number]
  status: string
  lastTested: string | null
  testing: boolean
  onTest: () => void
  onClose: () => void
}) {
  const connected = status === 'connected'
  return (
    <div className="border-t border-border bg-surface-2/30 px-5 py-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div>
          <SectionLabel className="mb-2">Connection</SectionLabel>
          <div className="space-y-1.5 text-[12px]">
            <div className="flex justify-between gap-4">
              <span className="text-faint">Status</span>
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <StatusDot tone={connected ? 'success' : 'neutral'} />
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-faint">MCP integration</span>
              <span className="mono text-muted">{integration.type}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-faint">Last test</span>
              <span className="text-muted">{lastTested ?? 'Not tested yet'}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-faint">Access</span>
              <span className="flex items-center gap-1 text-muted">
                <ShieldCheck className="h-3 w-3 text-muted" />
                Read-only MCP server
              </span>
            </div>
          </div>
        </div>
        <div>
          <SectionLabel className="mb-2">Permissions</SectionLabel>
          <div className="space-y-1">
            {integration.capabilities.map(cap => (
              <div key={cap} className="flex items-center gap-1.5 text-[12px] text-muted">
                <CheckCircle2 className="h-3 w-3 text-muted" />
                {cap}
              </div>
            ))}
          </div>
        </div>
        <div>
          <SectionLabel className="mb-2">Diagnostics</SectionLabel>
          <div className="flex items-center justify-between rounded-md border border-border bg-surface px-3 py-2">
            <div>
              <div className="text-[12px] font-medium text-foreground">Connection test</div>
              <div className="text-[10.5px] text-faint">
                {testing ? 'Testing endpoint…' : lastTested ? 'Endpoint responded' : 'Run to verify health'}
              </div>
            </div>
            <Button size="sm" variant={testing ? 'secondary' : 'outline'} onClick={onTest} disabled={testing || !connected}>
              {testing ? <RefreshCw className="h-3 w-3 animate-spin" /> : <TestTube className="h-3 w-3" />}
              {testing ? 'Testing' : 'Run test'}
            </Button>
          </div>
          {!connected && (
            <div className="mt-2 rounded-md border border-warning/25 bg-warning/5 px-3 py-2 text-[11px] text-warning">
              Reconnect to restore access for queries.
            </div>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="mt-3 flex items-center gap-1 text-[11.5px] text-faint transition-colors hover:text-muted cursor-pointer"
      >
        <ChevronDown className="h-3 w-3" /> Close details
      </button>
    </div>
  )
}

export default function SourcesPage() {
  const [connections, setConnections] = useState<Connection[]>([])
  const [testing, setTesting] = useState<string | null>(null)
  const [connecting, setConnecting] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [lastTested, setLastTested] = useState<Record<string, Date>>({})
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('connected')) {
      const type = params.get('connected')
      setNotice(
        `${INTEGRATIONS.find(i => i.type === type)?.label ?? type} connected successfully.`,
      )
    } else if (params.get('error')) {
      setNotice(`OAuth failed: ${params.get('error')}. Check the integration settings and try again.`)
    }
    window.history.replaceState({}, '', window.location.pathname)
    api.sources.list().then(setConnections).catch(() => {})
  }, [])

  const getStatus = (type: string) => connections.find(c => c.integration_type === type)?.status || 'disconnected'

  const handleConnect = async (type: string) => {
    setConnecting(type)
    try {
      const result = await api.sources.connect(type)
      if (result?.authorize_url) {
        window.location.href = result.authorize_url
        return
      }
      setConnections(await api.sources.list())
    } catch {
      // connection failed; status stays as-is
    }
    setConnecting(null)
  }

  const handleDisconnect = async (type: string) => {
    try {
      await api.sources.disconnect(type)
      setConnections(await api.sources.list())
    } catch {
      // disconnect failed; status stays as-is
    }
  }

  const handleTest = async (type: string) => {
    setTesting(type)
    try {
      await api.sources.test(type)
      setLastTested(prev => ({ ...prev, [type]: new Date() }))
    } catch {
      // test failed; no error UI
    }
    setTesting(null)
  }

  const connectedCount = connections.filter(c => c.status === 'connected').length

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-5xl px-8 py-7">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Connected Sources</h1>
            <p className="mt-0.5 text-[12.5px] text-muted">
              Manage the systems Nexus can access through MCP.
            </p>
          </div>
          <Badge tone={connectedCount === connections.length && connections.length > 0 ? 'success' : 'neutral'}>
            <StatusDot tone={connectedCount === connections.length ? 'success' : 'warning'} />
            {connectedCount}/{connections.length || 4} connected
          </Badge>
        </div>

        {notice && (
          <div className="mb-4 flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-[12px] text-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-muted" />
            {notice}
          </div>
        )}

        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          {INTEGRATIONS.map((integration, i) => {
            const status = getStatus(integration.type)
            const connected = status === 'connected'
            const isOpen = expanded === integration.type
            return (
              <div key={integration.type} className={cn(i > 0 && 'border-t border-border')}>
                {/* Row */}
                <button
                  type="button"
                  onClick={() => setExpanded(isOpen ? null : integration.type)}
                  className="flex w-full items-center gap-3.5 px-4 py-3 text-left transition-colors hover:bg-surface-2/50 cursor-pointer"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-2">
                    <SourceIcon type={integration.type} className="h-4 w-4 text-muted" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-medium text-foreground">{integration.label}</span>
                      {connected ? (
                        <Badge tone="success">
                          <StatusDot tone="success" />
                          Connected
                        </Badge>
                      ) : (
                        <Badge tone="neutral">Not connected</Badge>
                      )}
                    </div>
                    <div className="mt-0.5 truncate text-[11.5px] text-muted">{integration.description}</div>
                  </div>
                  <div className="hidden shrink-0 text-right sm:block">
                    <div className="text-[11px] tabular-nums text-muted">{integration.capabilities.length} permissions</div>
                    <div className="text-[10.5px] text-faint">MCP · read-only</div>
                  </div>
                  <ChevronRight className={cn('h-4 w-4 shrink-0 text-faint transition-transform', isOpen && 'rotate-90')} />
                </button>

                {/* Row actions */}
                {!isOpen && (
                  <div className="flex items-center gap-2 border-t border-border/60 bg-surface-2/30 px-4 py-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleTest(integration.type)}
                      disabled={!connected || testing === integration.type}
                    >
                      {testing === integration.type ? <RefreshCw className="h-3 w-3 animate-spin" /> : <TestTube className="h-3 w-3" />}
                      {testing === integration.type ? 'Testing…' : 'Test connection'}
                    </Button>
                    {connected ? (
                      <Button size="sm" variant="ghost" onClick={() => handleDisconnect(integration.type)}>
                        <Plug className="h-3 w-3" />
                        Disconnect
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => handleConnect(integration.type)}
                        disabled={connecting === integration.type}
                      >
                        {connecting === integration.type ? <RefreshCw className="h-3 w-3 animate-spin" /> : <PlugZap className="h-3 w-3" />}
                        {connecting === integration.type ? 'Connecting…' : 'Connect'}
                      </Button>
                    )}
                    {lastTested[integration.type] && (
                      <span className="ml-auto flex items-center gap-1 text-[10.5px] text-faint">
                        <Clock className="h-3 w-3" />
                        Last tested {timeAgo(lastTested[integration.type])}
                      </span>
                    )}
                  </div>
                )}

                {isOpen && (
                  <DetailPanel
                    integration={integration}
                    status={status}
                    lastTested={lastTested[integration.type] ? timeAgo(lastTested[integration.type]) : null}
                    testing={testing === integration.type}
                    onTest={() => handleTest(integration.type)}
                    onClose={() => setExpanded(null)}
                  />
                )}
              </div>
            )
          })}
        </div>

        <div className="mt-3 flex items-center gap-2 text-[11px] text-faint">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Connect each source to authorize live access. GitHub and Slack use OAuth; HubSpot uses a Private App token; PostgreSQL connects to the configured database.
        </div>
      </div>
    </div>
  )
}