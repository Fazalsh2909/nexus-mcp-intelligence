function parseDate(date: string | Date): Date {
  // Backend sends naive UTC datetimes ("2026-08-13T16:17:05.390166"); JS would
  // parse them as local time. Treat missing timezone info as UTC.
  if (typeof date === 'string' && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(date)) {
    return new Date(`${date}Z`)
  }
  return typeof date === 'string' ? new Date(date) : date
}

export function timeAgo(date: string | Date): string {
  const d = parseDate(date)
  const diff = Date.now() - d.getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 45) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min${minutes === 1 ? '' : 's'} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function formatClock(date: string | Date): string {
  const d = parseDate(date)
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function formatDateTime(date: string | Date): string {
  const d = parseDate(date)
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function formatNumber(n: number): string {
  return n.toLocaleString()
}

export const SOURCE_META: Record<string, { label: string; short: string }> = {
  github: { label: 'GitHub', short: 'GH' },
  slack: { label: 'Slack', short: 'SL' },
  hubspot: { label: 'HubSpot', short: 'HS' },
  postgres: { label: 'PostgreSQL', short: 'PG' },
  postgresql: { label: 'PostgreSQL', short: 'PG' },
}

export function sourceLabel(toolOrType: string): string {
  const t = toolOrType.toLowerCase()
  if (t.includes('github')) return 'GitHub'
  if (t.includes('slack')) return 'Slack'
  if (t.includes('hubspot')) return 'HubSpot'
  if (t.includes('postgres') || t.includes('sql')) return 'PostgreSQL'
  if (t.includes('openrouter') || t.includes('llm') || t.includes('answer')) return 'LLM'
  return toolOrType
}