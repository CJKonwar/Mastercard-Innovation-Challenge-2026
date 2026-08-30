import { useState } from 'react'
import { Panel, Tag, MetricCard, EmptyState } from '../components/ui'
import RunPanel from '../components/RunPanel'
import { Header } from './PromptInjection'
import { useResultsContext } from '../lib/ResultsContext'
import type { TokenReplayData } from '../data/types'

export default function TokenReplay() {
  const { data, refetch } = useResultsContext()
  const tr = data?.tokenReplay ?? null

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Token Replay · two-layer defence"
        subtitle="Not a loop over rounds — a funnel. A deterministic verifier handles what rules can decide; a risk scorer covers the gaps rules structurally cannot."
        status={tr ? `${tr.testSetSize.toLocaleString()} held-out events` : 'not run yet'}
      />

      <RunPanel
        vector="token-replay"
        title="Run the pipeline"
        note="fully local (LightGBM + deterministic checks) — no API quota used"
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
      <Panel title="Detection funnel" tags={<><Tag accent="blue">layer 1</Tag><Tag accent="amber">layer 2</Tag></>} note="which layer catches which sub-class — the division of labor is designed">
        <Funnel tr={tr} />
      </Panel>

      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
        <MetricCard label="Precision" value={tr.precision.toFixed(3)} accent="blue" />
        <MetricCard label="Recall" value={tr.recall.toFixed(3)} accent="blue" />
        <MetricCard label="F1 / AUC" value={tr.f1.toFixed(3)} accent="blue" sub={tr.auc !== null ? `AUC ${tr.auc.toFixed(3)}` : 'AUC undefined this run'} />
        <MetricCard label="False positives" value={`${((tr.confusion.fp / (tr.confusion.fp + tr.confusion.tn)) * 100).toFixed(2)}%`} accent="amber" sub="legitimate traffic" />
      </div>

      {sc && (
        <Panel title="Explore a sub-class" note="click a row to see how each layer handles it">
          <div className="flex flex-col gap-2.5">
            <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${tr.subclasses.length}, minmax(0,1fr))` }}>
              {tr.subclasses.map((s) => (
                <button
                  key={s.label}
                  onClick={() => setSelected(s.label)}
                  className="rounded-lg border px-3 py-2.5 text-left transition-colors"
                  style={{
                    borderColor: selected === s.label ? 'var(--blue-line)' : 'var(--rule)',
                    background: selected === s.label ? 'var(--blue-wash)' : 'var(--surface)',
                  }}
                >
                  <div className="text-[length:var(--text-xs)] font-semibold">{s.label}</div>
                  <div className="font-mono text-[length:var(--text-2xs)] mt-0.5" style={{ color: 'var(--muted)' }}>n={s.n}</div>
                </button>
              ))}
            </div>
            <div className="rounded-lg border p-3.5 mt-1" style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}>
              <div className="text-[length:var(--text-sm)] font-semibold mb-2">{sc.label}</div>
              <div className="flex gap-6">
                <LayerReadout label="Layer 1 (rules)" value={sc.layer1} />
                <LayerReadout label="Layer 2 (LightGBM)" value={sc.layer2} />
                <LayerReadout label="Combined" value={sc.combined} strong />
              </div>
              <p className="text-[length:var(--text-xs)] mt-2.5" style={{ color: 'var(--muted)' }}>
                {sc.layer1 === 1 && sc.layer2 === null && 'Decidable by rule alone — nonce reuse or context-hash mismatch never reaches Layer 2.'}
                {sc.layer1 === 0 && 'Layer 1 accepts this by design — it structurally cannot see it. This is Layer 2\'s entire reason for existing.'}
              </p>
            </div>
          </div>
        </Panel>
      )}

      <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <Panel title="Recall by difficulty tier" note="combined pipeline · from the team's evaluation report">
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
          <p className="text-[length:var(--text-xs)] mt-3" style={{ color: 'var(--muted)' }}>
            Full-hard (device, IP, and geo all preserved) still holds 100% recall — Layer 2's dominant
            features here are temporal, not spatial, which is exactly what full-hard is built to defeat.
          </p>
        </Panel>
        <Panel title="Why two layers" tags={<Tag accent="blue">design note</Tag>}>
          <div className="flex flex-col gap-2 text-[length:var(--text-xs)]" style={{ color: 'var(--ink-2)' }}>
            <p><strong>Layer 1</strong> is deterministic, auditable, exact: a nonce reused inside its TTL, or a context hash that doesn&rsquo;t match, is a rule violation. No model, no false positives possible.</p>
            <p><strong>The gap:</strong> once the sliding window passes, a replayed token looks fresh. T3 and T4 pass both deterministic gates cleanly — by design, not by accident.</p>
            <p><strong>Layer 2</strong> keeps device drift, geo distance, and time-since-issue as continuous features, so the model learns where the boundary sits for cases a hard rule cannot express.</p>
          </div>
        </Panel>
      </div>

      <Panel title="The feedback loop, run for real" note="entries from the team's own build log">
        <div className="flex flex-col gap-2.5">
          {tr.feedbackLoop.map((f, i) => (
            <div key={i} className="rounded-lg border p-3" style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}>
              <div className="flex items-center gap-2 mb-1.5">
                <Tag accent={f.tag === 'honest limitation' ? 'amber' : f.tag === 'real fix' ? 'red' : 'blue'}>{f.tag}</Tag>
                <span className="text-[length:var(--text-sm)] font-semibold">{f.title}</span>
              </div>
              <p className="text-[length:var(--text-xs)]" style={{ color: 'var(--ink-2)' }}>{f.body}</p>
              {f.before && f.after && (
                <div className="flex items-center gap-2 mt-2 font-mono text-[length:var(--text-xs)]">
                  <span className="line-through" style={{ color: 'var(--muted)' }}>{f.before}</span>
                  <span>→</span>
                  <span className="font-semibold" style={{ color: 'var(--red)' }}>{f.after}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </Panel>
    </>
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
    <div className="flex items-center gap-0 overflow-x-auto">
      {stages.map((s, i) => (
        <div key={s.label} className="flex items-center">
          <div className="rounded-lg border px-4 py-3 min-w-[150px] text-center" style={{ borderColor: 'var(--rule)' }}>
            <div className="text-[length:var(--text-xs)] font-semibold" style={{ color: s.color }}>{s.label}</div>
            <div className="font-mono text-[length:var(--text-lg)] font-semibold mt-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-[length:var(--text-2xs)] mt-0.5" style={{ color: 'var(--muted)' }}>{s.sub}</div>
          </div>
          {i < stages.length - 1 && (
            <svg width="28" height="20" className="shrink-0" aria-hidden="true">
              <line x1="2" y1="10" x2="24" y2="10" stroke="var(--ink-2)" strokeWidth="1.6" markerEnd="url(#tr-ar)" />
              <defs>
                <marker id="tr-ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M0 0 L10 5 L0 10 z" fill="var(--ink-2)" />
                </marker>
              </defs>
            </svg>
          )}
        </div>
      ))}
    </div>
  )
}
