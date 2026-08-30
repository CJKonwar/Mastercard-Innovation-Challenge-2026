import type { ReactNode } from 'react'
import type { Accent } from '../data'

const accentVar: Record<Accent | 'ink', string> = {
  red: 'var(--red)',
  blue: 'var(--blue)',
  amber: 'var(--amber)',
  violet: 'var(--violet)',
  ink: 'var(--ink)',
}

export function Panel({
  title, note, tags, children, className = '', accent = 'ink',
}: {
  title?: string
  note?: string
  tags?: ReactNode
  children: ReactNode
  className?: string
  accent?: Accent | 'ink'
}) {
  const color = accentVar[accent]
  return (
    <section
      className={`rounded-xl border overflow-hidden transition-shadow duration-200 hover:shadow-md ${className}`}
      style={{ background: 'var(--surface)', borderColor: 'var(--rule)', boxShadow: 'var(--shadow-sm)' }}
    >
      {title && (
        <div
          className="flex items-center gap-2.5 flex-wrap px-5 py-3.5 border-b-2"
          style={{ borderColor: accent === 'ink' ? 'var(--rule-soft)' : `var(--${accent}-line)`, background: 'var(--surface-2)' }}
        >
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
          <h2 className="text-[length:var(--text-md)] font-bold tracking-tight">{title}</h2>
          {tags}
          {note && (
            <span
              className="ml-auto text-[length:var(--text-xs)] font-medium px-2.5 py-1 rounded-full"
              style={{ background: 'var(--sunk)', color: 'var(--ink-2)' }}
            >
              {note}
            </span>
          )}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}

export function Tag({ children, accent = 'ink' }: { children: ReactNode; accent?: Accent | 'ink' }) {
  const wash = accent === 'ink' ? 'var(--sunk)' : `var(--${accent}-wash)`
  return (
    <span
      className="font-mono text-[length:var(--text-2xs)] font-medium px-1.5 py-0.5 rounded"
      style={{ background: wash, color: accentVar[accent] }}
    >
      {children}
    </span>
  )
}

/** Shared chrome for a card inside a list of cards (feedback-log entries, step
 * cards, elite payloads, ...) - one definition so every such list looks and
 * behaves the same instead of each page inventing its own border/padding/hover. */
export function ListCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${className}`}
      style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)', boxShadow: 'var(--shadow-sm)' }}
    >
      {children}
    </div>
  )
}

export function MetricCard({
  label, value, sub, accent = 'ink', trend,
}: {
  label: string
  value: ReactNode
  sub?: ReactNode
  accent?: Accent | 'ink'
  trend?: { dir: 'up' | 'down'; text: string; good?: boolean }
}) {
  return (
    <div
      className="relative overflow-hidden rounded-xl border p-4.5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
      style={{ background: 'var(--surface)', borderColor: 'var(--rule)', boxShadow: 'var(--shadow-sm)' }}
    >
      <div className="absolute left-0 top-0 bottom-0 w-1 rounded-r-full" style={{ background: accentVar[accent] }} />
      <div className="text-[length:var(--text-xs)] font-bold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>
        {label}
      </div>
      <div className="font-mono text-[length:var(--text-3xl)] font-bold tracking-tight mt-1.5 leading-none" style={{ color: 'var(--ink)' }}>{value}</div>
      {(sub || trend) && (
        <div className="text-[length:var(--text-sm)] mt-2" style={{ color: 'var(--muted)' }}>
          {trend && (
            <span
              className="font-mono font-semibold mr-1.5"
              style={{ color: trend.good === false ? 'var(--red)' : 'var(--blue)' }}
            >
              {trend.dir === 'up' ? '↑' : '↓'} {trend.text}
            </span>
          )}
          {sub}
        </div>
      )}
    </div>
  )
}

export function Pill({ children, tone }: { children: ReactNode; tone: 'blocked' | 'step' | 'allow' | 'caught' | 'evaded' }) {
  const map: Record<string, { bg: string; fg: string }> = {
    blocked: { bg: 'var(--red-wash)', fg: 'var(--red)' },
    evaded: { bg: 'var(--red-wash)', fg: 'var(--red)' },
    step: { bg: 'var(--amber-wash)', fg: 'var(--amber)' },
    allow: { bg: 'var(--blue-wash)', fg: 'var(--blue)' },
    caught: { bg: 'var(--blue-wash)', fg: 'var(--blue)' },
  }
  const c = map[tone]
  return (
    <span className="text-[length:var(--text-2xs)] font-semibold px-1.75 py-0.5 rounded-full" style={{ background: c.bg, color: c.fg }}>
      {children}
    </span>
  )
}

export function Field({
  label, value, onChange, options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <label className="flex flex-col gap-1 text-[length:var(--text-sm)]" style={{ color: 'var(--ink-2)' }}>
      <span className="eyebrow">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border px-2.5 py-1.5 text-[length:var(--text-sm)] font-medium outline-none"
        style={{ background: 'var(--surface)', borderColor: 'var(--rule)', color: 'var(--ink)' }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  )
}

export function EmptyState({ title, body }: { title: string; body: ReactNode }) {
  return (
    <div
      className="rounded-[10px] border border-dashed px-5 py-8 text-center"
      style={{ borderColor: 'var(--rule)', color: 'var(--muted)' }}
    >
      <div className="text-[length:var(--text-sm)] font-semibold mb-1.5" style={{ color: 'var(--ink-2)' }}>{title}</div>
      <p className="text-[length:var(--text-xs)] max-w-[52ch] mx-auto leading-relaxed">{body}</p>
    </div>
  )
}

export function StatusPill({ live, children }: { live: boolean; children: ReactNode }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[length:var(--text-xs)] font-semibold rounded-full px-2.5 py-1 whitespace-nowrap"
      style={live
        ? { color: 'var(--blue)', background: 'var(--blue-wash)', border: '1px solid var(--blue-line)' }
        : { color: 'var(--muted)', background: 'var(--sunk)', border: '1px solid var(--rule)' }}
    >
      {live && <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: 'currentColor' }} />}
      {children}
    </span>
  )
}
