import { useState } from 'react'
import { Play, FlaskConical, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'
import { api } from '../lib/api'
import { Badge, Button, Card, EmptyState, StatusDot } from '../lib/ui'

export default function EvaluationsPage() {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<{ status: string; message: string } | null>(null)
  const [error, setError] = useState('')

  const runSuite = async () => {
    setRunning(true)
    setError('')
    setResult(null)
    try {
      const res = await api.evaluations.run()
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run evaluation suite')
    }
    setRunning(false)
  }

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl px-8 py-7">
        <div className="mb-5">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Evaluations</h1>
          <p className="mt-0.5 text-[12.5px] text-muted">
            Automated test suites that verify Nexus answers against expected outcomes.
          </p>
        </div>

        <Card className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-surface-2">
                <FlaskConical className="h-4 w-4 text-muted" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-semibold text-foreground">Evaluation suite</span>
                  <Badge tone={running ? 'warning' : 'success'}>
                    <StatusDot tone={running ? 'warning' : 'success'} pulse={running} />
                    {running ? 'Running' : 'Ready'}
                  </Badge>
                </div>
                <p className="mt-1 max-w-md text-[12px] leading-relaxed text-muted">
                  Runs predefined queries against the connected sources and scores the
                  answers. Results are recorded server-side.
                </p>
              </div>
            </div>
            <Button variant="secondary" className="border-transparent bg-success text-[#0D0D0F] hover:bg-success/90" onClick={runSuite} disabled={running}>
              {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              {running ? 'Running…' : 'Run suite'}
            </Button>
          </div>

          {error && (
            <div className="mt-4 rounded-md border border-danger/25 bg-danger/5 px-3 py-2.5 text-[12px] text-danger">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-4 overflow-hidden rounded-md border border-border">
              <div className="flex items-center justify-between bg-surface-2/50 px-3.5 py-2.5">
                <span className="flex items-center gap-2 text-[12px] font-medium text-foreground">
                  {result.status === 'completed' ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5 text-warning" />
                  )}
                  {result.status}
                </span>
                <span className="mono text-[10.5px] text-faint">POST /api/v1/evaluations/run</span>
              </div>
              <div className="px-3.5 py-3 text-[12.5px] leading-relaxed text-muted">{result.message}</div>
            </div>
          )}
        </Card>

        <div className="mt-4">
          <EmptyState
            icon={FlaskConical}
            title="No evaluation cases defined yet"
            description="Evaluation cases are defined server-side. Run the suite to verify the current set against the connected sources."
          />
        </div>
      </div>
    </div>
  )
}