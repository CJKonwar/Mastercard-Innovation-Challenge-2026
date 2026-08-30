import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { VECTORS, type Accent } from '../data'

interface Stage {
  slug: string
  eyebrow: string
  title: string
  input: string
  vector: string
  loopType: 'closed loop' | 'static pipeline'
  metricLabel: string
  detail: string
  arrowLabel: string
}

const STAGES: Stage[] = [
  {
    slug: 'prompt-injection',
    eyebrow: 'Stage 1',
    title: 'Agent reads context',
    input: 'reviews · receipts · invoices',
    vector: 'Prompt Injection',
    loopType: 'closed loop',
    metricLabel: 'attack success rate',
    detail: 'A MAP-Elites red team searches a 288-niche space (6 surfaces × 6 techniques × 8 objectives) of indirect prompt injections. A 3-tier fused detector — content, provenance graph, intent — decides allow / step-up / block per action.',
    arrowLabel: 'decision',
  },
  {
    slug: 'token-replay',
    eyebrow: 'Stage 2',
    title: 'Agent authorizes payment',
    input: 'delegated token · nonce · TTL',
    vector: 'Token Replay',
    loopType: 'static pipeline',
    metricLabel: 'breach rate, combined',
    detail: 'A two-layer verifier extends a peer-reviewed zero-trust baseline: Layer 1 (context-hash binding + nonce registry) disposes of clear-cut replay deterministically; Layer 2 (LightGBM) catches leakage-based misuse Layer 1 was never designed to see.',
    arrowLabel: 'charge',
  },
  {
    slug: 'merchant-fraud',
    eyebrow: 'Stage 3',
    title: 'Payment routes to merchant',
    input: 'merchant risk profile',
    vector: 'Merchant Fraud',
    loopType: 'closed loop',
    metricLabel: 'evasion rate',
    detail: 'CTGAN learns the joint distribution of real fraud, then generates candidates steered by evasion + realism objectives. Hard-negative mining folds back exactly the candidates the current classifier gets wrong, hardening the decision boundary.',
    arrowLabel: 'settlement',
  },
  {
    slug: 'graph-fraud',
    eyebrow: 'Stage 4',
    title: 'Money settles across rails',
    input: 'cross-rail transaction graph',
    vector: 'Graph Fraud',
    loopType: 'closed loop',
    metricLabel: 'combined F1, latest epoch',
    detail: 'A dual-head heterogeneous graph transformer scores mule accounts (node head) and cross-rail laundering hops (edge head) jointly, hardened over real adversarial epochs where the red team mutates toward whatever the blue team just missed.',
    arrowLabel: '',
  },
]

const accentOf = (slug: string): Accent => VECTORS.find((v) => v.slug === slug)!.accent
const accentVar: Record<Accent, string> = { red: 'var(--red)', blue: 'var(--blue)', amber: 'var(--amber)', violet: 'var(--violet)' }
const accentLine: Record<Accent, string> = { red: 'var(--red-line)', blue: 'var(--blue-line)', amber: 'var(--amber-line)', violet: 'var(--violet-line)' }
const accentWash: Record<Accent, string> = { red: 'var(--red-wash)', blue: 'var(--blue-wash)', amber: 'var(--amber-wash)', violet: 'var(--violet-wash)' }

export default function PaymentFlowDiagram({ metrics }: { metrics: Record<string, string> }) {
  const [active, setActive] = useState<string | null>(null)
  const navigate = useNavigate()
  const shown = STAGES.find((s) => s.slug === active) ?? null

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-0" style={{ gridTemplateColumns: `repeat(${STAGES.length}, minmax(0,1fr))` }}>
        {STAGES.map((s, i) => {
          const accent = accentOf(s.slug)
          return (
          <div key={s.slug} className="flex items-stretch">
            <button
              onMouseEnter={() => setActive(s.slug)}
              onFocus={() => setActive(s.slug)}
              onClick={() => navigate(`/${s.slug}`)}
              className="group flex-1 text-left rounded-[9px] border p-3 transition-all duration-150 cursor-pointer"
              style={{
                background: 'var(--surface)',
                borderColor: active === s.slug ? accentLine[accent] : 'var(--rule)',
                borderWidth: active === s.slug ? 1.6 : 1,
                boxShadow: active === s.slug ? 'var(--shadow-md)' : 'var(--shadow-sm)',
                transform: active === s.slug ? 'translateY(-2px)' : 'none',
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="eyebrow">{s.eyebrow}</span>
                <span
                  className="text-[length:var(--text-2xs)] font-mono px-1.5 py-0.5 rounded"
                  style={{ background: 'var(--sunk)', color: 'var(--muted)' }}
                >
                  {s.loopType === 'closed loop' ? 'loop' : 'static'}
                </span>
              </div>
              <div className="text-[length:var(--text-sm)] font-bold mt-1 leading-snug">{s.title}</div>
              <div className="font-mono text-[length:var(--text-2xs)] mt-1" style={{ color: 'var(--muted)' }}>{s.input}</div>
              <div className="h-px my-2" style={{ background: 'var(--rule-soft)' }} />
              <div className="text-[length:var(--text-xs)] font-semibold" style={{ color: accentVar[accent] }}>{s.vector}</div>
              <div className="font-mono text-[length:var(--text-xl)] font-semibold mt-1" style={{ color: accentVar[accent] }}>
                {metrics[s.slug] ?? '—'}
              </div>
              <div className="text-[length:var(--text-2xs)] font-mono" style={{ color: 'var(--muted)' }}>{s.metricLabel}</div>
            </button>
            {i < STAGES.length - 1 && (
              <div className="flex flex-col items-center justify-center px-2 w-14 shrink-0">
                <FlowArrow label={s.arrowLabel} markerId={`flow-arrow-${i}`} />
              </div>
            )}
          </div>
        )})}
      </div>

      <div
        className="rounded-[9px] border px-4 py-3 text-[length:var(--text-sm)] leading-relaxed transition-all"
        style={{
          background: shown ? accentWash[accentOf(shown.slug)] : 'var(--surface-2)',
          borderColor: shown ? accentLine[accentOf(shown.slug)] : 'var(--rule-soft)',
          color: 'var(--ink-2)',
          minHeight: 60,
        }}
      >
        {shown ? (
          <>
            <span className="font-semibold" style={{ color: accentVar[accentOf(shown.slug)] }}>{shown.vector}. </span>
            {shown.detail}
          </>
        ) : (
          <span style={{ color: 'var(--muted)' }}>Hover a stage to see how it works. Click to open its full page.</span>
        )}
      </div>

      <p className="text-[length:var(--text-xs)]" style={{ color: 'var(--muted)' }}>
        <span className="font-mono">loop</span> = attacker and defense co-evolve round over round.{' '}
        <span className="font-mono">static</span> = evaluated once against a fixed dataset, no adversarial retraining.
      </p>
    </div>
  )
}

function FlowArrow({ label, markerId }: { label: string; markerId: string }) {
  return (
    <div className="relative w-full h-6 flex items-center">
      <svg viewBox="0 0 56 24" width="100%" height="24" className="overflow-visible" aria-hidden="true">
        <defs>
          <marker id={markerId} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill="var(--ink-2)" />
          </marker>
        </defs>
        <line x1="2" y1="12" x2="48" y2="12" stroke="var(--ink-2)" strokeWidth="1.6" markerEnd={`url(#${markerId})`} />
        <circle r="2" fill="var(--blue)">
          <animateMotion dur="2.4s" repeatCount="indefinite" path="M2,12 L46,12" />
        </circle>
      </svg>
      {label && (
        <span
          className="absolute -top-3.5 left-1/2 -translate-x-1/2 font-mono text-[length:var(--text-2xs)] whitespace-nowrap"
          style={{ color: 'var(--muted)' }}
        >
          {label}
        </span>
      )}
    </div>
  )
}
