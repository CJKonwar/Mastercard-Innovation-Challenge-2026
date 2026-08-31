import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Panel, MetricCard, EmptyState } from '../components/ui'
import { useResultsContext } from '../lib/ResultsContext'
import { VECTORS, type Accent } from '../data'

const accentOf = (slug: string): Accent => VECTORS.find((v) => v.slug === slug)!.accent

interface ArchStep { label: string; detail: string }
interface VectorArchInfo { slug: string; name: string; stage: string; accent: Accent; steps: ArchStep[] }

// Full architecture diagrams from the team's own Solution Walkthrough
// (Figures A1, 5, 2, and A3), one per vector, saved to public/arch/.
const ARCH_DIAGRAM: Record<string, string> = {
  'prompt-injection': '/arch/prompt-injection.png',
  'token-replay': '/arch/token-replay.png',
  'merchant-fraud': '/arch/merchant-fraud.png',
  'graph-fraud': '/arch/graph-fraud.png',
}

// Same 3 stages every vector runs, so one icon per stage name reads
// consistently across all four cards.
const STEP_ICON: Record<string, React.ReactNode> = {
  Identify: <><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>,
  Generate: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />,
  Defend: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
}

// Grounded in the team's own Solution Walkthrough (§4-7): the real
// Identify -> Generate -> Defend mechanism each vector runs, not a generic
// restatement of "identify, generate, defend."
const VECTOR_ARCH: VectorArchInfo[] = [
  {
    slug: 'prompt-injection', name: 'Prompt Injection', stage: 'Checkout decision', accent: 'red',
    steps: [
      { label: 'Identify', detail: '288-niche space — 6 commerce surfaces × 6 evasion techniques × 8 financial objectives' },
      { label: 'Generate', detail: 'Local Qwen3-8B mutates payloads inside a MAP-Elites quality-diversity search over the archive' },
      { label: 'Defend', detail: '3-tier fusion (content, provenance graph, intent) → allow / step-up / block, judged by a deterministic outcome checker that never calls an LLM' },
    ],
  },
  {
    slug: 'token-replay', name: 'Token Replay', stage: 'Consent & token issuance', accent: 'blue',
    steps: [
      { label: 'Identify', detail: '4 sub-types (T1–T4) pinned to specific steps of the real Agent Pay trust chain' },
      { label: 'Generate', detail: 'Legitimate sessions cloned and corrupted in exactly one field, across 4 difficulty tiers' },
      { label: 'Defend', detail: 'Layer 1 — nonce registry + context-hash binding — catches T1/T2 deterministically; Layer 2 LightGBM catches the leakage-based T3/T4 cases Layer 1 structurally cannot see' },
    ],
  },
  {
    slug: 'merchant-fraud', name: 'Merchant Fraud', stage: 'Onboarding', accent: 'amber',
    steps: [
      { label: 'Identify', detail: '22 features across merchant profile, onboarding behavior, and 90-day post-onboarding transactions' },
      { label: 'Generate', detail: 'CTGAN candidates steered by evasion, fraud-preservation, and realism objectives together, via a differentiable surrogate of the Blue-Team classifier' },
      { label: 'Defend', detail: '3 gates (domain bounds → realism discriminator → hard-negative mining) feed a fresh Blue-Team MLP retrained from scratch' },
    ],
  },
  {
    slug: 'graph-fraud', name: 'Graph Fraud', stage: 'Post-transaction settlement', accent: 'violet',
    steps: [
      { label: 'Identify', detail: 'Two surfaces of one laundering op — mule accounts (device/IP sharing, PageRank) and cross-rail arbitrage (dwell time, rail sequence)' },
      { label: 'Generate', detail: 'A graph topology simulator decides who sends to whom; CTGAN decides amount, timing, rail — gated by a 4-test fidelity validator' },
      { label: 'Defend', detail: 'A Dual-Head Heterogeneous Graph Transformer, hardened over real adversarial epochs with an FPR guardrail that self-corrects an over-flagging blue team' },
    ],
  },
]

export default function Overview() {
  const [zoomedSlug, setZoomedSlug] = useState<string | null>(null)
  const { data, loading } = useResultsContext()
  const pi = data?.promptInjection ?? null
  const tr = data?.tokenReplay ?? null
  const mf = data?.merchantFraud ?? null
  const gf = data?.graphFraud ?? null

  const piLast = pi?.history[pi.history.length - 1]
  const gfLast = gf?.epochs[gf.epochs.length - 1]
  const gfFirst = gf?.epochs[0]

  const cardData: Record<string, { hasData: boolean; metric: string; sub: string }> = {
    'prompt-injection': piLast
      ? { hasData: true, metric: `${(piLast.mutationAsr * 100).toFixed(0)}%`, sub: 'attack success rate' }
      : { hasData: false, metric: '—', sub: '' },
    'token-replay': tr
      ? { hasData: true, metric: `F1 ${tr.f1.toFixed(3)}`, sub: `on ${tr.testSetSize.toLocaleString()} events` }
      : { hasData: false, metric: '—', sub: '' },
    'merchant-fraud': mf
      ? { hasData: true, metric: `${(mf.evasionRate * 100).toFixed(1)}%`, sub: `${(mf.detectionRate * 100).toFixed(1)}% detection` }
      : { hasData: false, metric: '—', sub: '' },
    'graph-fraud': gfLast
      ? { hasData: true, metric: gfLast.combined_f1.toFixed(3), sub: `combined F1 · from ${gfFirst!.combined_f1.toFixed(3)}` }
      : { hasData: false, metric: '—', sub: '' },
  }

  return (
    <div className="flex flex-col gap-5">
      <div
        className="relative overflow-hidden rounded-xl border pl-6 pr-5 py-4.5"
        style={{ background: 'var(--surface)', borderColor: 'var(--rule)', boxShadow: 'var(--shadow-sm)' }}
      >
        <span
          className="absolute left-0 top-0 bottom-0 w-1.5"
          style={{ background: 'linear-gradient(180deg, var(--red), var(--blue) 34%, var(--amber) 67%, var(--violet))' }}
        />
        <div className="flex items-start gap-3">
          <img src="/mastercard-logo.svg" alt="" className="h-9 w-auto shrink-0 mt-0.5" />
          <div>
            <h1 className="text-[length:var(--text-2xl)] font-extrabold tracking-tight leading-tight">Mastercard Innovation Challenge</h1>
            <div className="text-[length:var(--text-xs)] font-bold tracking-wide mt-1" style={{ color: 'var(--ink-2)' }}>Team Bias Bros</div>
          </div>
        </div>
        <div
          className="flex items-start gap-2.5 mt-3 rounded-lg px-3.5 py-2.5 max-w-[62ch]"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--rule-soft)' }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--ink-2)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <p className="text-[length:var(--text-sm)] leading-relaxed" style={{ color: 'var(--ink-2)' }}>
            Four independently built defenses, each hardening a different stage of one agentic-payment
            lifecycle — measured against real held-out data, not asserted.
          </p>
        </div>
      </div>

      <Panel title="Four architectures, one lifecycle" note="each vector's real Identify → Generate → Defend pipeline">
        {loading ? (
          <div className="text-[length:var(--text-sm)]" style={{ color: 'var(--muted)' }}>Loading live results…</div>
        ) : (
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))' }}>
            {VECTOR_ARCH.map((info) => (
              <VectorArchCard key={info.slug} info={info} {...cardData[info.slug]} onZoom={() => setZoomedSlug(info.slug)} />
            ))}
          </div>
        )}
      </Panel>

      <div className="grid gap-4" style={{ gridTemplateColumns: '1.1fr 1fr' }}>
        <Panel title="The convergent idea" note="why these four are one system">
          <ConvergentIdea />
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

      {zoomedSlug && (
        <ArchZoomModal
          info={VECTOR_ARCH.find((v) => v.slug === zoomedSlug)!}
          onClose={() => setZoomedSlug(null)}
        />
      )}
    </div>
  )
}

function ArchZoomModal({ info, onClose }: { info: VectorArchInfo; onClose: () => void }) {
  const color = `var(--${info.accent})`
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      style={{ background: 'rgba(20, 24, 31, 0.72)' }}
      onClick={onClose}
    >
      <div
        className="relative rounded-xl border overflow-hidden flex flex-col"
        style={{ background: 'var(--surface)', borderColor: color, boxShadow: 'var(--shadow-md)', maxWidth: '94vw', maxHeight: '92vh' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-5 py-3.5 border-b shrink-0" style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}>
          <span className="text-[length:var(--text-md)] font-bold" style={{ color }}>{info.name} — architecture</span>
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 text-[length:var(--text-xs)] font-bold px-2.5 py-1.5 rounded-md shrink-0"
            style={{ background: `var(--${info.accent}-wash)`, color }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            Close
          </button>
        </div>
        <div className="overflow-auto p-4" style={{ background: '#fff' }}>
          <img src={ARCH_DIAGRAM[info.slug]} alt={`${info.name} architecture diagram, full size`} className="block" style={{ maxWidth: '100%' }} />
        </div>
      </div>
    </div>
  )
}

const CONVERGENT_POINTS: { slug: string; name: string; accent: Accent; insight: string }[] = [
  { slug: 'prompt-injection', name: 'Prompt Injection', accent: 'red', insight: 'A payment argument traced back to the untrusted text it actually came from.' },
  { slug: 'token-replay', name: 'Token Replay', accent: 'blue', insight: 'A token judged by the cryptographic context it was scoped for, not the traffic around it.' },
  { slug: 'graph-fraud', name: 'Graph Fraud', accent: 'violet', insight: 'A device-sharing pattern read as a graph topology, not shrunk into a scalar count.' },
  { slug: 'merchant-fraud', name: 'Merchant Fraud', accent: 'amber', insight: "A classifier's own decision boundary hardened directly, not diluted with more average examples." },
]

function ConvergentIdea() {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-[length:var(--text-sm)] leading-relaxed" style={{ color: 'var(--ink-2)' }}>
        Built independently by different team members, against different data and different threat models,
        all four detectors arrive at the same underlying move: stop scoring what an action{' '}
        <em style={{ color: 'var(--ink)' }}>looks like</em> and start scoring where it{' '}
        <em style={{ color: 'var(--ink)' }}>came from</em>.
      </p>

      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))' }}>
        {CONVERGENT_POINTS.map((p) => {
          const color = `var(--${p.accent})`
          const wash = `var(--${p.accent}-wash)`
          return (
            <Link
              key={p.slug}
              to={`/${p.slug}`}
              className="group relative overflow-hidden flex gap-3 rounded-xl border p-3.5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
              style={{ borderColor: 'var(--rule)', background: 'var(--surface-2)' }}
            >
              <span className="absolute left-0 top-0 bottom-0 w-1 rounded-r-full" style={{ background: color }} />
              <span className="flex items-center justify-center w-8 h-8 rounded-full shrink-0" style={{ background: wash }}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
                  <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
                </svg>
              </span>
              <div className="min-w-0">
                <div className="text-[length:var(--text-xs)] font-bold" style={{ color }}>{p.name}</div>
                <p className="text-[length:var(--text-xs)] leading-relaxed mt-0.5" style={{ color: 'var(--ink-2)' }}>{p.insight}</p>
              </div>
              <span
                className="ml-auto self-center shrink-0 text-[length:var(--text-sm)] font-bold opacity-0 -translate-x-1 transition-all duration-200 group-hover:opacity-100 group-hover:translate-x-0"
                style={{ color }}
              >
                →
              </span>
            </Link>
          )
        })}
      </div>

      <p className="text-[length:var(--text-sm)] font-bold" style={{ color: 'var(--ink)' }}>
        Provenance over pattern matching discovered convergently, four separate times.
      </p>
    </div>
  )
}

function VectorArchCard({
  info, hasData, metric, sub, onZoom,
}: {
  info: VectorArchInfo
  hasData: boolean
  metric: string
  sub: string
  onZoom: () => void
}) {
  const [flipped, setFlipped] = useState(false)
  const color = `var(--${info.accent})`
  const wash = `var(--${info.accent}-wash)`

  // Auto-revert to the front after a spell of no interaction, so a card
  // doesn't stay flipped indefinitely once someone's attention has moved on.
  const revertTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hovered = useRef(false)

  const clearRevertTimer = () => {
    if (revertTimer.current) { clearTimeout(revertTimer.current); revertTimer.current = null }
  }
  const scheduleRevert = () => {
    clearRevertTimer()
    if (!hovered.current) revertTimer.current = setTimeout(() => setFlipped(false), 15000)
  }

  useEffect(() => {
    if (flipped) scheduleRevert()
    else clearRevertTimer()
    return clearRevertTimer
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flipped])

  return (
    <div
      style={{ perspective: 1600 }}
      onMouseEnter={() => { hovered.current = true; clearRevertTimer() }}
      onMouseLeave={() => { hovered.current = false; if (flipped) scheduleRevert() }}
    >
      <div
        className="relative transition-transform duration-700"
        style={{ transformStyle: 'preserve-3d', transform: flipped ? 'rotateY(180deg)' : 'none', minHeight: 320 }}
      >
        {/* FRONT */}
        <div
          className="relative overflow-hidden rounded-xl border p-4.5"
          style={{
            background: 'var(--surface)', borderColor: 'var(--rule)', boxShadow: 'var(--shadow-sm)',
            backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden',
          }}
        >
      <span className="absolute left-0 top-0 bottom-0 w-1 rounded-r-full" style={{ background: color }} />

      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-[length:var(--text-md)] font-bold" style={{ color }}>{info.name}</div>
          <div className="text-[length:var(--text-xs)] mt-0.5 font-medium" style={{ color: 'var(--muted)' }}>{info.stage}</div>
        </div>
        {hasData ? (
          <div className="text-right shrink-0">
            <div className="font-mono text-[length:var(--text-xl)] font-bold leading-none" style={{ color }}>{metric}</div>
            <div className="text-[length:var(--text-2xs)] mt-1" style={{ color: 'var(--muted)' }}>{sub}</div>
          </div>
        ) : (
          <span className="text-[length:var(--text-2xs)] font-bold px-2 py-1 rounded-full shrink-0" style={{ background: 'var(--sunk)', color: 'var(--muted)' }}>
            not run yet
          </span>
        )}
      </div>

      <div className="flex flex-col mt-4">
        {info.steps.map((s, i) => (
          <div key={s.label} className="flex gap-3">
            <div className="flex flex-col items-center shrink-0">
              <span
                className="flex items-center justify-center w-7 h-7 rounded-full"
                style={{ background: wash }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
                  {STEP_ICON[s.label]}
                </svg>
              </span>
              {i < info.steps.length - 1 && <span className="w-px flex-1" style={{ background: 'var(--rule)', minHeight: 18 }} />}
            </div>
            <div className={i < info.steps.length - 1 ? 'pb-3' : ''}>
              <div className="text-[length:var(--text-xs)] font-bold uppercase tracking-wide" style={{ color }}>{s.label}</div>
              <div className="text-[length:var(--text-xs)] mt-0.5 leading-relaxed" style={{ color: 'var(--ink-2)' }}>{s.detail}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 mt-1">
        <button
          onClick={() => setFlipped(true)}
          className="flex items-center gap-1.5 text-[length:var(--text-xs)] font-bold px-2.5 py-1.5 rounded-md transition-colors"
          style={{ background: 'var(--sunk)', color: 'var(--ink-2)' }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
            <path d="M6.5 10v4a2 2 0 002 2H14" />
          </svg>
          Show arch
        </button>
        <Link
          to={`/${info.slug}`}
          className="group flex items-center gap-1 text-[length:var(--text-xs)] font-semibold"
          style={{ color: 'var(--muted)' }}
        >
          Open full page
          <span className="transition-transform group-hover:translate-x-0.5" style={{ color }}>→</span>
        </Link>
      </div>
        </div>

        {/* BACK */}
        <div
          className="absolute inset-0 rounded-xl border p-3.5 flex flex-col"
          style={{
            background: 'var(--surface)', borderColor: color, boxShadow: 'var(--shadow-sm)',
            backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden',
            transform: 'rotateY(180deg)',
          }}
        >
          <div className="flex items-center justify-between gap-2 mb-2.5 shrink-0">
            <span className="text-[length:var(--text-sm)] font-bold" style={{ color }}>{info.name} — architecture</span>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={onZoom}
                className="flex items-center gap-1.5 text-[length:var(--text-xs)] font-bold px-2.5 py-1.5 rounded-md"
                style={{ background: wash, color }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  <line x1="11" y1="8" x2="11" y2="14" />
                  <line x1="8" y1="11" x2="14" y2="11" />
                </svg>
                Zoom
              </button>
              <button
                onClick={() => setFlipped(false)}
                className="flex items-center gap-1.5 text-[length:var(--text-xs)] font-bold px-2.5 py-1.5 rounded-md"
                style={{ background: 'var(--sunk)', color: 'var(--ink-2)' }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                Back
              </button>
            </div>
          </div>
          <button
            onClick={onZoom}
            className="group/zoom relative flex-1 min-h-0 rounded-lg border overflow-hidden flex items-center justify-center cursor-zoom-in"
            style={{ borderColor: 'var(--rule-soft)', background: '#fff' }}
          >
            <img
              src={ARCH_DIAGRAM[info.slug]}
              alt={`${info.name} architecture diagram`}
              className="w-full h-full object-contain"
            />
            <div
              className="absolute inset-0 flex items-center justify-center gap-1.5 opacity-0 group-hover/zoom:opacity-100 transition-opacity text-[length:var(--text-xs)] font-bold"
              style={{ background: 'rgba(20, 24, 31, 0.55)', color: '#fff' }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="11" y1="8" x2="11" y2="14" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
              Click to enlarge
            </div>
          </button>
        </div>
      </div>
    </div>
  )
}
