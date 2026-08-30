import { NavLink, Outlet } from 'react-router-dom'
import { VECTORS, type Accent } from '../data'
import { useResultsContext } from '../lib/ResultsContext'

export default function Layout() {
  const { backendUp, refetch } = useResultsContext()
  return (
    <div className="grid min-h-screen" style={{ gridTemplateColumns: '260px minmax(0,1fr)' }}>
      <aside
        className="flex flex-col gap-5 p-4 border-r"
        style={{ background: 'var(--surface-2)', borderColor: 'var(--rule)' }}
      >
        <div className="flex flex-col gap-1">
          <span className="flex items-center gap-2 text-[length:var(--text-base)] font-bold tracking-tight">
            <span
              className="w-2.5 h-2.5 rounded-[2px] inline-block"
              style={{ background: 'var(--red)', boxShadow: '5px 0 0 var(--blue)' }}
            />
            AI Defense Lab
          </span>
          <small style={{ color: 'var(--muted)' }} className="text-[length:var(--text-xs)]">
            Mastercard Innovation Challenge &middot; Team Bias Bros
          </small>
        </div>

        <NavItem to="/" label="Overview" sub="The whole lab, one page" end />

        <div className="flex flex-col gap-1.5">
          <div className="eyebrow mb-0.5">Attack vectors</div>
          {VECTORS.map((v) => (
            <NavItem key={v.slug} to={`/${v.slug}`} label={v.name} sub={v.short} accent={v.accent} />
          ))}
        </div>

        <div className="mt-auto text-[length:var(--text-xs)] leading-relaxed" style={{ color: 'var(--muted)' }}>
          Sandboxed simulation — no real payment rails, no live cards, no customer data.
        </div>
      </aside>

      <main className="min-w-0 px-6 py-5 pb-10 flex flex-col gap-4">
        {backendUp === false && (
          <div
            className="flex items-center justify-between gap-3 rounded-lg border px-3.5 py-2.5 text-[length:var(--text-sm)]"
            style={{ borderColor: 'var(--amber-line)', background: 'var(--amber-wash)', color: 'var(--amber)' }}
          >
            <span>
              <strong>Backend not reachable.</strong> Live data and run controls need the API server —
              start it with <code className="font-mono">uvicorn app.main:app --port 8000</code> from{' '}
              <code className="font-mono">web/backend</code>.
            </span>
            <button onClick={() => refetch()} className="font-semibold underline shrink-0">Retry</button>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  )
}

function NavItem({
  to, label, sub, accent, end,
}: {
  to: string
  label: string
  sub: string
  accent?: Accent
  end?: boolean
}) {
  const line = accent ? `var(--${accent}-line)` : 'var(--rule)'
  const wash = accent ? `var(--${accent}-wash)` : 'var(--sunk)'
  const solid = accent ? `var(--${accent})` : 'var(--ink)'
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `relative overflow-hidden rounded-lg border px-2.75 py-2 text-left transition-colors ${
          isActive ? '' : 'hover:border-[var(--faint)]'
        }`
      }
      style={({ isActive }) => ({
        background: isActive ? wash : 'var(--surface)',
        borderColor: isActive ? line : 'var(--rule)',
      })}
    >
      {({ isActive }) => (
        <>
          <span
            className="absolute left-0 top-0 bottom-0 w-[3px]"
            style={{ background: isActive ? solid : (accent ? line : 'var(--rule)') }}
          />
          <div className="pl-1.5">
            <div className="text-[length:var(--text-sm)] font-semibold">{label}</div>
            <div className="text-[length:var(--text-2xs)]" style={{ color: 'var(--muted)' }}>{sub}</div>
          </div>
        </>
      )}
    </NavLink>
  )
}
