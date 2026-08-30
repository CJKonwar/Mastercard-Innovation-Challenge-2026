import { Link } from 'react-router-dom'
import { Panel, MetricCard, EmptyState } from '../components/ui'
import PaymentFlowDiagram from '../components/PaymentFlowDiagram'
import { useResultsContext } from '../lib/ResultsContext'
import { VECTORS, type Accent } from '../data'

const accentOf = (slug: string): Accent => VECTORS.find((v) => v.slug === slug)!.accent

export default function Overview() {
  const { data, loading } = useResultsContext()
  const pi = data?.promptInjection ?? null
  const tr = data?.tokenReplay ?? null
  const mf = data?.merchantFraud ?? null
  const gf = data?.graphFraud ?? null

  const piLast = pi?.history[pi.history.length - 1]
  const gfLast = gf?.epochs[gf.epochs.length - 1]
  const gfFirst = gf?.epochs[0]

  const flowMetrics: Record<string, string> = {
    'prompt-injection': piLast ? `${(piLast.mutationAsr * 100).toFixed(0)}%` : '—',
    'token-replay': tr ? `${(100 - tr.recall * 100).toFixed(1)}%` : '—',
    'merchant-fraud': mf ? `${(mf.evasionRate * 100).toFixed(1)}%` : '—',
    'graph-fraud': gfLast ? gfLast.combined_f1.toFixed(3) : '—',
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-[length:var(--text-xl)] font-bold">AI Defense Lab</h1>
          <p className="text-[length:var(--text-sm)] mt-1 max-w-[62ch]" style={{ color: 'var(--muted)' }}>
            Four independently built defenses, each hardening a different stage of one agentic-payment
            lifecycle — measured against real held-out data, not asserted.
          </p>
        </div>
        <span
          className="text-[length:var(--text-xs)] font-semibold rounded-full px-2.75 py-1 border"
          style={{ color: 'var(--muted)', background: 'var(--sunk)', borderColor: 'var(--rule)' }}
        >
          4 vectors &middot; Team Bias Bros
        </span>
      </div>

      <Panel title="One payment, four attack surfaces" note="hover a stage · click to open">
        <PaymentFlowDiagram metrics={flowMetrics} />
      </Panel>

      <Panel title="Current state, all four vectors">
        {loading ? (
          <div className="text-[length:var(--text-sm)]" style={{ color: 'var(--muted)' }}>Loading live results…</div>
        ) : (
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
            {piLast ? (
              <VectorCard to="/prompt-injection" name="Prompt Injection"
                value={`${(piLast.mutationAsr * 100).toFixed(0)}%`}
                sub={`attack success · ${(piLast.mutationDetection * 100).toFixed(0)}% detection`}
                go={`${pi!.archiveSize}/${pi!.totalCells} niches claimed`} />
            ) : <NotRunCard to="/prompt-injection" name="Prompt Injection" />}
            {tr ? (
              <VectorCard to="/token-replay" name="Token Replay"
                value={`F1 ${tr.f1.toFixed(3)}`}
                sub={`precision ${tr.precision.toFixed(3)} · recall ${tr.recall.toFixed(3)}`}
                go={`${tr.testSetSize.toLocaleString()} held-out events`} />
            ) : <NotRunCard to="/token-replay" name="Token Replay" />}
            {mf ? (
              <VectorCard to="/merchant-fraud" name="Merchant Fraud"
                value={`${(mf.evasionRate * 100).toFixed(1)}%`}
                sub={`evasion · ${(mf.detectionRate * 100).toFixed(1)}% detection`}
                go={`${mf.generated.toLocaleString()} candidates generated`} />
            ) : <NotRunCard to="/merchant-fraud" name="Merchant Fraud" />}
            {gfLast ? (
              <VectorCard to="/graph-fraud" name="Graph Fraud"
                value={gfLast.combined_f1.toFixed(3)}
                sub={`combined F1 · from ${gfFirst!.combined_f1.toFixed(3)} at epoch 0`}
                go={`${gf!.epochs.length} adversarial epochs`} />
            ) : <NotRunCard to="/graph-fraud" name="Graph Fraud" />}
          </div>
        )}
      </Panel>

      <div className="grid gap-4" style={{ gridTemplateColumns: '1.1fr 1fr' }}>
        <Panel title="The convergent idea" note="why these four are one system">
          <p className="text-[length:var(--text-sm)] leading-relaxed" style={{ color: 'var(--ink-2)' }}>
            Built independently by different team members, against different data and different threat
            models, all four detectors arrive at the same underlying move: stop scoring what an action{' '}
            <em>looks like</em> and start scoring where it <em>came from</em>. A payment argument traced
            back to untrusted text (Prompt Injection), a token judged by the cryptographic context it was
            scoped for (Token Replay), a device-sharing pattern read as a graph topology rather than a
            scalar count (Graph Fraud), and a classifier's own decision boundary hardened directly rather
            than diluted with more average examples (Merchant Fraud) — provenance over pattern-matching,
            discovered convergently four separate times.
          </p>
        </Panel>
        <Panel title="Headline metrics" note="one number per vector, live from disk">
          {pi || tr || mf || gf ? (
            <div className="grid gap-2.5" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))' }}>
              <MetricCard label="PI archive coverage" value={pi ? `${pi.archiveSize}/${pi.totalCells}` : '—'} accent={accentOf('prompt-injection')} sub="MAP-Elites niches claimed" />
              <MetricCard label="Token replay AUC" value={tr?.auc?.toFixed(3) ?? '—'} accent={accentOf('token-replay')} sub={tr ? `on ${tr.testSetSize.toLocaleString()} events` : 'not run yet'} />
              <MetricCard label="Merchant fraud detection" value={mf ? `${(mf.detectionRate * 100).toFixed(1)}%` : '—'} accent={accentOf('merchant-fraud')} sub="CTGAN-augmented MLP" />
              <MetricCard
                label="Graph fraud FPR"
                value={gfLast ? `${(gfLast.node_fpr_test * 100).toFixed(2)}%` : '—'}
                accent={accentOf('graph-fraud')}
                trend={gfFirst && gfLast ? { dir: 'down', text: `from ${(gfFirst.node_fpr_test * 100).toFixed(2)}%`, good: true } : undefined}
              />
            </div>
          ) : (
            <EmptyState title="No results yet" body="Run any vector from its own page to see live metrics here." />
          )}
        </Panel>
      </div>

      <p className="text-[length:var(--text-xs)] leading-relaxed" style={{ color: 'var(--muted)' }}>
        A fifth vector — deepfake-enabled identity &amp; authentication spoofing, cross-cutting onboarding,
        consent, and step-up authentication — is in active development and not yet represented here.
        Sandboxed simulation throughout: no real payment rails, no live cards, no customer data.
      </p>
    </div>
  )
}

function VectorCard({
  to, name, value, sub, go,
}: {
  to: string
  name: string
  value: string
  sub: string
  go: string
}) {
  const color = `var(--${accentOf(to.slice(1))})`
  return (
    <Link
      to={to}
      className="group relative overflow-hidden rounded-[9px] border p-3.5 block transition-transform hover:-translate-y-0.5"
      style={{ background: 'var(--surface)', borderColor: 'var(--rule)', boxShadow: 'var(--shadow-sm)' }}
    >
      <span className="absolute left-0 top-0 bottom-0 w-[3px]" style={{ background: color }} />
      <div className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-wider" style={{ color: 'var(--muted)' }}>{name}</div>
      <div className="font-mono text-[length:var(--text-2xl)] font-semibold tracking-tight mt-1 leading-none" style={{ color }}>{value}</div>
      <div className="text-[length:var(--text-xs)] mt-1.5" style={{ color: 'var(--muted)' }}>{sub}</div>
      <div className="text-[length:var(--text-2xs)] mt-2 flex items-center gap-1 font-medium" style={{ color: 'var(--muted)' }}>
        {go}
        <span className="transition-transform group-hover:translate-x-0.5" style={{ color }}>→</span>
      </div>
    </Link>
  )
}

function NotRunCard({ to, name }: { to: string; name: string }) {
  return (
    <Link
      to={to}
      className="relative overflow-hidden rounded-[9px] border border-dashed p-3.5 block flex flex-col justify-center items-start"
      style={{ borderColor: 'var(--rule)', color: 'var(--muted)' }}
    >
      <div className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-wider">{name}</div>
      <div className="text-[length:var(--text-sm)] mt-1.5">Not run yet — open page to start it →</div>
    </Link>
  )
}
