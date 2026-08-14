import * as React from 'react'
import { api, type Analytics, type ChatSession } from './api'

export interface UserInfo {
  id: string
  email: string
  name: string
}

interface WorkspaceState {
  sources: Array<{ id: string; integration_type: string; status: string }>
  sessions: ChatSession[]
  analytics: Analytics | null
  user: UserInfo | null
  loading: boolean
  refresh: () => Promise<void>
}

const WorkspaceContext = React.createContext<WorkspaceState>({
  sources: [],
  sessions: [],
  analytics: null,
  user: null,
  loading: true,
  refresh: async () => {},
})

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [sources, setSources] = React.useState<WorkspaceState['sources']>([])
  const [sessions, setSessions] = React.useState<ChatSession[]>([])
  const [analytics, setAnalytics] = React.useState<Analytics | null>(null)
  const [user, setUser] = React.useState<UserInfo | null>(null)
  const [loading, setLoading] = React.useState(true)

  const load = React.useCallback(async () => {
    try {
      const [src, sess, an, me] = await Promise.all([
        api.sources.list(),
        api.chat.sessions(),
        api.analytics.get(),
        api.auth.me(),
      ])
      setSources(src)
      setSessions(sess)
      setAnalytics(an)
      setUser(me)
    } catch {
      // individual endpoints may be unavailable; keep partial state
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    load()
  }, [load])

  return (
    <WorkspaceContext.Provider
      value={{
        sources,
        sessions,
        analytics,
        user,
        loading,
        refresh: load,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useWorkspace() {
  return React.useContext(WorkspaceContext)
}

export function connectedCount(sources: WorkspaceState['sources']): number {
  return sources.filter(s => s.status === 'connected').length
}