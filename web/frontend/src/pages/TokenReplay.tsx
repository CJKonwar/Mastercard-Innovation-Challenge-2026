import { useState } from 'react'
import { Panel, Tag, MetricCard, ListCard, EmptyState } from '../components/ui'
import RunPanel from '../components/RunPanel'
import { Header } from './PromptInjection'
import { useResultsContext } from '../lib/ResultsContext'
import type { TokenReplayData } from '../data/types'

// What generator.py actually derives for each label (derive_T1/T2/T3_T4) -
// not a taxonomy asserted after the fact.
const SUBCLASS_INFO: Record<string, { name: string; blurb: string; icon: React.ReactNode }> = {
  T1: {
    name: 'Same-context replay', blurb: 'Token reused minutes later for the same merchant — only device, network, or location differs.',
    icon: <><path d="M17 1l4 4-4 4" /><path d="M3 11V9a4 4 0 014-4h14" /><path d="M7 23l-4-4 4-4" /><path d="M21 13v2a4 4 0 01-4 4H3" /></>,
  },
  T2: {
    name: 'Cross-context replay', blurb: 'Same token, but charged to a different merchant than it was scoped for — the context hash no longer matches.',
    icon: <><polyline points="16 3 21 3 21 8" /><line x1="4" y1="20" x2="21" y2="3" /><polyline points="21 16 21 21 16 21" /><line x1="15" y1="15" x2="21" y2="21" /><line x1="4" y1="4" x2="9" y2="9" /></>,
  },
  T3: {
    name: 'Leakage-induced misuse', blurb: 'Token harvested from logs or traces, replayed hours to days later — merchant unchanged, so the hash still matches.',
    icon: <path d="M12 2.69l5.66 5.66a8 8 0 11-11.31 0z" />,
  },
  T4: {
    name: 'Observability-based replay', blurb: 'Same delayed harvested-token mechanism as T3, tracked as its own reporting bucket.',
    icon: <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></>,
  },
}

const FEEDBACK_STYLE: Record<string, { color: string; wash: string; line: string; icon: React.ReactNode }> = {
  'real fix': {
    color: 'var(--red)', wash: 'var(--red-wash)', line: 'var(--red-line)',
    icon: <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z" />,
  },
  'robustness check': {
    color: 'var(--blue)', wash: 'var(--blue-wash)', line: 'var(--blue-line)',
    icon: <><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0114.13-3.36L23 10M1 14l5.36 4.36A9 9 0 0020.49 15" /></>,
  },
  'honest limitation': {
    color: 'var(--amber)', wash: 'var(--amber-wash)', line: 'var(--amber-line)',
    icon: <><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>,
  },
}

export default function TokenReplay() {
  const { data, refetch } = useResultsContext()
  const tr = data?.tokenReplay ?? null

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Token Replay · two-layer defence"
        subtitle="Not a loop over rounds — a funnel. A deterministic verifier handles what rules can decide; a risk scorer covers the gaps rules structurally cannot."
        status={tr ? `${tr.testSetSize.toLocaleString()} held-out events` : 'not run yet'}
        accent="blue"
      />

      <RunPanel
        vector="token-replay"
        title="Run the pipeline"
        note="fully local (LightGBM + deterministic checks) — no API quota used"
        accent="blue"
        onDone={refetch}
        fields={[
          { key: 'skipGenerate', kind: 'checkbox', label: 'Data', defaultValue: true, help: 'Reuse existing sessions.csv (faster)' },
          { key: 'withMining', kind: 'checkbox', label: 'Extras', defaultValue: false, help: 'Also run failure mining (diagnostic)' },
        ]}
      />

      {tr ? <Dashboard tr={tr} /> : (
        <EmptyState title="No results yet" body="Run the pipeline above — with existing data reused it finishes in well under a minute." />
      )}
    </div>
  )
}

function Dashboard({ tr }: { tr: TokenReplayData }) {
  const [selected, setSelected] = useState(tr.subclasses[Math.min(2, tr.subclasses.length - 1)]?.label)
  const sc = tr.subclasses.find((s) => s.label === selected) ?? tr.subclasses[0]

  return (
    <>
      <Panel title="Detection funnel" tags={<><Tag accent="blue">layer 1</Tag><Tag accent="amber">layer 2</Tag></>} note="which layer catches which sub-class — the division of labor is designed" accent="blue">
        <Funnel tr={tr} />
      </Panel>

      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
        <MetricCard label="Precision" value={tr.precision.toFixed(3)} accent="blue" />
        <MetricCard label="Recall" value={tr.recall.toFixed(3)} accent="blue" />
        <MetricCard label="F1 / AUC" value={tr.f1.toFixed(3)} accent="blue" sub={tr.auc !== null ? `AUC ${tr.auc.toFixed(3)}` : 'AUC undefined this run'} />
        <MetricCard label="False positives" value={`${((tr.confusion.fp / (tr.confusion.fp + tr.confusion.tn)) * 100).toFixed(2)}%`} accent="amber" sub="legitimate traffic" />
      </div>

      {sc && (
        <Panel title="Explore a sub-class" note="click a card to see how each layer handles it" accent="blue">
          <div className="flex flex-col gap-3.5">
            <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${tr.subclasses.length}, minmax(0,1fr))` }}>
              {tr.subclasses.map((s) => {
                const info = SUBCLASS_INFO[s.label]
                const isActive = selected === s.label
                return (
                  <button
                    key={s.label}
                    onClick={() => setSelected(s.label)}
                    className="rounded-xl border px-4 py-3.5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
                    style={{
                      borderColor: isActive ? 'var(--blue-line)' : 'var(--rule)',
                      background: isActive ? 'var(--blue-wash)' : 'var(--surface)',
                      boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className="flex items-center justify-center w-8 h-8 rounded-full shrink-0"
                        style={{ background: isActive ? 'var(--surface)' : 'var(--blue-wash)' }}
                      >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          {info?.icon}
                        </svg>
                      </span>
                      <span className="font-mono text-[length:var(--text-2xs)]" style={{ color: 'var(--muted)' }}>n={s.n}</span>
                    </div>
                    <div className="font-mono text-[length:var(--text-sm)] font-bold mt-2" style={{ color: isActive ? 'var(--blue)' : 'var(--ink)' }}>{s.label}</div>
                    <div className="text-[length:var(--text-xs)] font-bold mt-0.5" style={{ color: 'var(--ink-2)' }}>{info?.name}</div>
                    <p className="text-[length:var(--text-xs)] leading-relaxed mt-1" style={{ color: 'var(--ink-2)' }}>{info?.blurb}</p>
                  </button>
                )
              })}
            </div>
            <div className="rounded-xl border p-4 mt-1" style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}>
              <div className="flex items-center gap-2.5 mb-2.5">
                <span className="flex items-center justify-center w-8 h-8 rounded-full shrink-0" style={{ background: 'var(--blue-wash)' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    {SUBCLASS_INFO[sc.label]?.icon}
                  </svg>
                </span>
                <div className="text-[length:var(--text-sm)] font-bold">{sc.label} — {SUBCLASS_INFO[sc.label]?.name}</div>
              </div>
              <div className="flex gap-7">
                <LayerReadout label="Layer 1 (rules)" value={sc.layer1} />
                <LayerReadout label="Layer 2 (LightGBM)" value={sc.layer2} />
                <LayerReadout label="Combined" value={sc.combined} strong />
              </div>
              <p className="text-[length:var(--text-xs)] mt-3 leading-relaxed" style={{ color: 'var(--ink-2)' }}>
                {sc.layer1 === 1 && sc.layer2 === null && 'Decidable by rule alone — nonce reuse or context-hash mismatch never reaches Layer 2.'}
                {sc.layer1 === 0 && 'Layer 1 accepts this by design — it structurally cannot see it. This is Layer 2\'s entire reason for existing.'}
              </p>
            </div>
          </div>
        </Panel>
      )}

      <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <Panel title="Recall by difficulty tier" note="combined pipeline · from the team's evaluation report" accent="blue">
          <div className="flex flex-col gap-2">
            {tr.difficultyTiers.map((t) => (
              <div key={t.label} className="flex items-center gap-3">
                <span className="text-[length:var(--text-sm)] w-[128px] shrink-0">{t.label}</span>
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--sunk)' }}>
                  <div className="h-full rounded-full" style={{ width: `${t.combinedRecall * 100}%`, background: 'var(--blue)' }} />
                </div>
                <span className="font-mono text-[length:var(--text-xs)] w-16 text-right" style={{ color: 'var(--muted)' }}>{(t.combinedRecall * 100).toFixed(0)}% · n={t.n}</span>
              </div>
            ))}
          </div>
          <p className="text-[length:var(--text-xs)] mt-3 leading-relaxed" style={{ color: 'var(--ink-2)' }}>
            Full-hard (device, IP, and geo all preserved) still holds 100% recall — Layer 2's dominant
            features here are temporal, not spatial, which is exactly what full-hard is built to defeat.
          </p>
        </Panel>
        <Panel title="Why two layers" tags={<Tag accent="blue">design note</Tag>} accent="blue">
          <div className="flex flex-col gap-3">
            <WhyLayerCard
              color="var(--blue)" wash="var(--blue-wash)"
              icon={<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></>}
              title="Layer 1"
              body="Deterministic, auditable, exact: a nonce reused inside its TTL, or a context hash that doesn't match, is a rule violation. No model, no false positives possible."
            />
            <WhyLayerCard
              color="var(--amber)" wash="var(--amber-wash)"
              icon={<><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>}
              title="The gap"
              body="Once the sliding window passes, a replayed token looks fresh. T3 and T4 pass both deterministic gates cleanly — by design, not by accident."
            />
            <WhyLayerCard
              color="var(--blue)" wash="var(--blue-wash)"
              icon={<path d="M3 3v18h18M18.7 8l-5.1 5.1-3-3L4 15.5" />}
              title="Layer 2"
              body="Keeps device drift, geo distance, and time-since-issue as continuous features, so the model learns where the boundary sits for cases a hard rule cannot express."
            />
          </div>
        </Panel>
      </div>

      <Panel title="The feedback loop, run for real" note="entries from the team's own build log" accent="blue">
        <div className="flex flex-col">
          {tr.feedbackLoop.map((f, i) => {
            const info = FEEDBACK_STYLE[f.tag] ?? FEEDBACK_STYLE['robustness check']
            const isLast = i === tr.feedbackLoop.length - 1
            return (
              <div key={i} className="flex gap-3.5">
                <div className="flex flex-col items-center shrink-0">
                  <span
                    className="flex items-center justify-center w-9 h-9 rounded-full border-2 shrink-0"
                    style={{ background: info.wash, borderColor: info.line }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={info.color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      {info.icon}
                    </svg>
                  </span>
                  {!isLast && <span className="w-px flex-1 my-1" style={{ background: 'var(--rule)', minHeight: 16 }} />}
                </div>
                <div className={`flex-1 min-w-0 ${isLast ? '' : 'pb-3.5'}`}>
                  <ListCard>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <Tag accent={f.tag === 'honest limitation' ? 'amber' : f.tag === 'real fix' ? 'red' : 'blue'}>{f.tag}</Tag>
                      <span className="text-[length:var(--text-sm)] font-bold">{f.title}</span>
                    </div>
                    <p className="text-[length:var(--text-xs)] leading-relaxed" style={{ color: 'var(--ink-2)' }}>{f.body}</p>
                    {f.before && f.after && (
                      <div className="flex items-center gap-2.5 mt-3 rounded-lg px-3 py-2 w-fit" style={{ background: 'var(--red-wash)' }}>
                        <span className="line-through font-mono text-[length:var(--text-xs)]" style={{ color: 'var(--muted)' }}>{f.before}</span>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--red)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M5 12h14M13 6l6 6-6 6" />
                        </svg>
                        <span className="font-mono font-bold text-[length:var(--text-xs)]" style={{ color: 'var(--red)' }}>{f.after}</span>
                      </div>
                    )}
                  </ListCard>
                </div>
              </div>
            )
          })}
        </div>
      </Panel>
    </>
  )
}

function WhyLayerCard({
  color, wash, icon, title, body,
}: {
  color: string
  wash: string
  icon: React.ReactNode
  title: string
  body: string
}) {
  return (
    <div
      className="flex gap-3 rounded-xl border p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
      style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}
    >
      <span className="flex items-center justify-center w-9 h-9 rounded-full shrink-0" style={{ background: wash }}>
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          {icon}
        </svg>
      </span>
      <div>
        <div className="text-[length:var(--text-sm)] font-bold" style={{ color }}>{title}</div>
        <p className="text-[length:var(--text-xs)] leading-relaxed mt-0.5" style={{ color: 'var(--ink-2)' }}>{body}</p>
      </div>
    </div>
  )
}

function LayerReadout({ label, value, strong }: { label: string; value: number | null; strong?: boolean }) {
  return (
    <div>
      <div className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-wide" style={{ color: 'var(--muted)' }}>{label}</div>
      <div className="font-mono text-[length:var(--text-lg)] font-semibold mt-0.5" style={{ color: value === null ? 'var(--faint)' : strong ? 'var(--blue)' : value === 0 ? 'var(--red)' : 'var(--ink)' }}>
        {value === null ? '—' : `${(value * 100).toFixed(0)}%`}
      </div>
    </div>
  )
}

function Funnel({ tr }: { tr: TokenReplayData }) {
  const total = tr.testSetSize
  const l1Rejected = tr.subclasses.filter((s) => s.layer1 === 1).reduce((a, s) => a + s.n, 0)
  const l2Handled = tr.subclasses.filter((s) => s.layer1 === 0).reduce((a, s) => a + s.n, 0)
  const stages = [
    { label: 'SESSIONS', value: total.toLocaleString(), sub: `${tr.fraudCount.toLocaleString()} fraudulent`, color: 'var(--ink)' },
    { label: 'LAYER 1 · rules', value: l1Rejected.toLocaleString(), sub: 'T1 + T2 rejected here', color: 'var(--blue)' },
    { label: 'LAYER 2 · model', value: l2Handled.toLocaleString(), sub: 'T3 + T4 caught here', color: 'var(--amber)' },
    { label: 'VERDICT', value: `F1 ${tr.f1.toFixed(3)}`, sub: `${((tr.confusion.fp / total) * 100).toFixed(2)}% false positives`, color: 'var(--blue)' },
  ]
  return (
    <div className="grid gap-0" style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0,1fr))` }}>
      {stages.map((s, i) => (
        <div key={s.label} className="flex items-stretch min-w-0">
          <div
            className="rounded-xl border px-4.5 py-4 flex-1 min-w-0 text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
            style={{ borderColor: 'var(--rule)', background: 'var(--surface)', boxShadow: 'var(--shadow-sm)' }}
          >
            <div className="text-[length:var(--text-xs)] font-bold uppercase tracking-wide" style={{ color: s.color }}>{s.label}</div>
            <div className="font-mono text-[length:var(--text-2xl)] font-bold mt-1.5" style={{ color: s.color }}>{s.value}</div>
            <div className="text-[length:var(--text-xs)] mt-1" style={{ color: 'var(--muted)' }}>{s.sub}</div>
          </div>
          {i < stages.length - 1 && (
            <div className="flex items-center justify-center w-9 shrink-0">
              <svg width="26" height="20" aria-hidden="true">
                <line x1="2" y1="10" x2="22" y2="10" stroke="var(--ink-2)" strokeWidth="1.8" markerEnd="url(#tr-ar)" />
                <defs>
                  <marker id="tr-ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                    <path d="M0 0 L10 5 L0 10 z" fill="var(--ink-2)" />
                  </marker>
                </defs>
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
