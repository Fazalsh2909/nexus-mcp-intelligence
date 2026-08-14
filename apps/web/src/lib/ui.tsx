import * as React from 'react'
import { Github, Slack, Building2, Database, ChevronDown } from 'lucide-react'
import { cn } from './utils'

/* ---------------------------------- Button --------------------------------- */

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type ButtonSize = 'sm' | 'md'

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-primary-foreground hover:bg-primary/90 border border-transparent shadow-sm',
  secondary:
    'bg-surface-2 text-foreground hover:bg-surface-2/80 border border-border',
  outline: 'bg-transparent text-foreground hover:bg-surface-2 border border-border-strong',
  ghost: 'bg-transparent text-muted hover:text-foreground hover:bg-surface-2 border border-transparent',
  danger:
    'bg-transparent text-danger hover:bg-danger/10 border border-danger/30',
}

const buttonSizes: Record<ButtonSize, string> = {
  sm: 'h-7 px-2.5 text-xs gap-1.5 rounded-md',
  md: 'h-8 px-3.5 text-[13px] gap-2 rounded-lg',
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'secondary', size = 'md', type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        'inline-flex items-center justify-center font-medium whitespace-nowrap transition-colors cursor-pointer select-none',
        'disabled:opacity-45 disabled:pointer-events-none active:opacity-90',
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = 'Button'

/* ----------------------------------- Card ---------------------------------- */

export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-surface',
        className,
      )}
      {...props}
    />
  )
}

export function CardHeader({
  title,
  description,
  action,
  className,
}: {
  title: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex items-start justify-between gap-3 px-4 pt-3.5 pb-3 border-b border-border', className)}>
      <div className="min-w-0">
        <h3 className="text-[13px] font-semibold text-foreground">{title}</h3>
        {description && <p className="text-xs text-muted mt-0.5">{description}</p>}
      </div>
      {action}
    </div>
  )
}

/* ---------------------------------- Badge ---------------------------------- */

type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'primary'

const badgeTones: Record<BadgeTone, string> = {
  neutral: 'text-muted bg-surface-2 border-border',
  success: 'text-success bg-surface-2 border-border',
  warning: 'text-warning bg-surface-2 border-border',
  danger: 'text-danger bg-surface-2 border-border',
  info: 'text-info bg-surface-2 border-border',
  primary: 'text-primary bg-surface-2 border-border',
}

export function Badge({
  tone = 'neutral',
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 h-[18px] px-1.5 rounded border text-[11px] font-medium whitespace-nowrap',
        badgeTones[tone],
        className,
      )}
      {...props}
    />
  )
}

/* -------------------------------- StatusDot -------------------------------- */

export function StatusDot({
  tone,
  className,
  pulse,
}: {
  tone: 'success' | 'warning' | 'danger' | 'neutral' | 'info'
  className?: string
  pulse?: boolean
}) {
  const colors: Record<string, string> = {
    success: 'bg-success',
    warning: 'bg-warning',
    danger: 'bg-danger',
    info: 'bg-info',
    neutral: 'bg-faint',
  }
  return (
    <span
      aria-hidden
      className={cn(
        'inline-block h-[7px] w-[7px] rounded-full shrink-0',
        colors[tone],
        pulse && 'trace-pulse',
        className,
      )}
    />
  )
}

/* ---------------------------------- Inputs --------------------------------- */

export const inputClass =
  'h-8 w-full rounded-md border border-border bg-surface-2/60 px-3 text-[13px] text-foreground placeholder:text-faint transition-colors focus:outline-none focus:border-primary/50 focus:bg-surface-2'

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(inputClass, className)} {...props} />
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="relative inline-block">
      <select
        className={cn(inputClass, 'appearance-none pr-7 cursor-pointer', className)}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-faint" />
    </div>
  )
}

/* -------------------------------- EmptyState ------------------------------- */

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ComponentType<{ className?: string }>
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-14 px-6', className)}>
      {Icon && (
        <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md border border-border bg-surface-2">
          <Icon className="h-4 w-4 text-muted" />
        </div>
      )}
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-xs leading-relaxed text-muted">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

/* --------------------------------- Skeleton -------------------------------- */

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn('rounded bg-surface-2 animate-pulse', className)}
      aria-hidden
    />
  )
}

/* -------------------------------- SourceIcon ------------------------------- */

export function SourceIcon({
  type,
  className,
}: {
  type: string
  className?: string
}) {
  const t = type.toLowerCase()
  if (t.includes('github')) return <Github className={className} />
  if (t.includes('slack')) return <Slack className={className} />
  if (t.includes('hubspot')) return <Building2 className={className} />
  return <Database className={className} />
}

/* ------------------------------- SourceChip -------------------------------- */

export function SourceChip({
  type,
  className,
}: {
  type: string
  className?: string
}) {
  const t = type.toLowerCase()
  const label = t.includes('github')
    ? 'GitHub'
    : t.includes('slack')
      ? 'Slack'
      : t.includes('hubspot')
        ? 'HubSpot'
        : 'PostgreSQL'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 text-[11px] font-medium text-muted',
        className,
      )}
    >
      <SourceIcon type={t} className="h-3 w-3 text-faint" />
      {label}
    </span>
  )
}

/* ---------------------------------- Kbd ------------------------------------ */

export function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="kbd">{children}</kbd>
}

/* ------------------------------- SectionLabel ------------------------------ */

export function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'text-[10.5px] font-semibold uppercase tracking-[0.08em] text-faint',
        className,
      )}
    >
      {children}
    </div>
  )
}