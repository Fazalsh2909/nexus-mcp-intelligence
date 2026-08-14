import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Zap, ShieldCheck, Loader2 } from 'lucide-react'
import { api } from '../lib/api'
import { clearLoggedOutFlag } from '../lib/auth'
import { Button, Input } from '../lib/ui'
import { cn } from '../lib/utils'

type Mode = 'login' | 'register'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<Mode>('login')
  const [apiStatus, setApiStatus] = useState<string>('')
  const navigate = useNavigate()

  useEffect(() => {
    api.meta
      .health()
      .then(h => setApiStatus(h.status))
      .catch(() => setApiStatus('unreachable'))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'register') {
        await api.auth.register(email, name, password)
      }
      const { access_token } = await api.auth.login(email, password)
      localStorage.setItem('nexus_token', access_token)
      localStorage.removeItem('nexus_last_session')
      clearLoggedOutFlag()
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : `${mode === 'register' ? 'Registration' : 'Login'} failed`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-surface-2">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Nexus</h1>
        </div>

        <div className="rounded-lg border border-border bg-surface p-5">
          <div className="mb-4 flex rounded-md border border-border bg-background p-0.5">
            {(['login', 'register'] as const).map(m => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setMode(m)
                  setError('')
                }}
                className={cn(
                  'flex-1 rounded py-1.5 text-[12px] font-medium transition-colors cursor-pointer',
                  mode === m ? 'bg-surface-2 text-foreground' : 'text-muted hover:text-foreground',
                )}
              >
                {m === 'login' ? 'Sign in' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {mode === 'register' && (
              <div>
                <label className="mb-1 block text-[11.5px] font-medium text-muted">Name</label>
                <Input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="Your name" required />
              </div>
            )}
            <div>
              <label className="mb-1 block text-[11.5px] font-medium text-muted">Email</label>
              <Input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" required />
            </div>
            <div>
              <label className="mb-1 block text-[11.5px] font-medium text-muted">Password</label>
              <Input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
            </div>

            {error && (
              <div className="rounded-md border border-danger/25 bg-danger/5 px-3 py-2 text-[12px] text-danger">
                {error}
              </div>
            )}

            <Button variant="primary" type="submit" disabled={loading} className="w-full">
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowRight className="h-3.5 w-3.5" />}
              {loading ? 'Connecting…' : mode === 'register' ? 'Create account' : 'Sign in'}
            </Button>
          </form>
        </div>

        <div className="mt-5 flex items-center justify-center gap-4 text-[10.5px] text-faint">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="h-3 w-3" /> JWT secured
          </span>
          <span>·</span>
          <span>API: {apiStatus ? (apiStatus === 'ok' ? 'online' : apiStatus) : 'checking…'}</span>
        </div>
      </div>
    </div>
  )
}