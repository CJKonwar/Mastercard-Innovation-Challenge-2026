import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Panel, Tag, MetricCard, Pill, EmptyState } from '../components/ui'
import RunPanel from '../components/RunPanel'
import { Header } from './PromptInjection'
import { useResultsContext } from '../lib/ResultsContext'
import type { MerchantFraudData } from '../data/types'

export default function MerchantFraud() {
  const { data, refetch } = useResultsContext()
  const mf = data?.merchantFraud ?? null

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Merchant Fraud · adversarial augmentation"
        subtitle="A generation campaign, not a round-based loop. CTGAN produces fraud candidates; whatever evades the classifier is precisely what gets fed back into training."
        status={mf ? `${mf.generated.toLocaleString()} candidates` : 'not run yet'}
      />

      <RunPanel
        vector="merchant-fraud"
        title="Run the campaign"
        note="fully local (CTGAN + Keras) — no API quota used"
        onDone={refetch}
        fields={[
          { key: 'samples', kind: 'number', label: 'Candidates to generate', defaultValue: 5000, min: 100, max: 20000 },
        ]}
      />

      {mf ? <Dashboard mf={mf} /> : (
        <EmptyState title="No campaign run yet" body="Start one above — try a smaller batch (500-1000) first if you just want to see the pipeline work." />
      )}
    </div>
  )
}

function Dashboard({ mf }: { mf: MerchantFraudData }) {
  const [selected, setSelected] = useState(0)
  const sample = mf.evadedSamples[Math.min(selected, mf.evadedSamples.length - 1)]

  return (
    <>
      <Panel title="Generate → filter → mine" tags={<><Tag accent="red">red</Tag><Tag accent="blue">blue</Tag></>} note="the evaded column is the product, not the failure">
        <PipelineDiagram mf={mf} />
      </Panel>

      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
        <MetricCard label="Detection" value={`${(mf.detectionRate * 100).toFixed(1)}%`} accent="blue" sub={`${mf.detected.toLocaleString()} of ${mf.validTested.toLocaleString()} caught`} />
        <MetricCard label="Evasion" value={`${(mf.evasionRate * 100).toFixed(1)}%`} accent="red" sub={`${mf.evaded} hard negatives harvested`} />
        <MetricCard label="Mean confidence" value={mf.meanFraudProb.toFixed(3)} accent="amber" sub="classifier probability on generated fraud" />
        <MetricCard label="Threshold" value={mf.threshold.toFixed(2)} accent="blue" sub="decision boundary" />
      </div>

      <Panel title="Augmentation lifts every metric" note="pre- vs. post-CTGAN augmentation, from the team's held-out ablation">
        <TrainCurveChart rows={mf.trainCurve} />
      </Panel>

      {sample && (
        <Panel title="Explore an evaded candidate" note="real synthetic profiles that beat the classifier — click through them">
          <div className="flex gap-1.5 mb-4 flex-wrap">
            {mf.evadedSamples.map((_, i) => (
              <button
                key={i}
                onClick={() => setSelected(i)}
                className="w-8 h-8 rounded-md border text-[length:var(--text-xs)] font-mono font-semibold"
                style={{
                  borderColor: selected === i ? 'var(--red-line)' : 'var(--rule)',
                  background: selected === i ? 'var(--red-wash)' : 'var(--surface)',
                  color: selected === i ? 'var(--red)' : 'var(--ink-2)',
                }}
              >
                {i + 1}
              </button>
            ))}
          </div>
          <div className="grid gap-4" style={{ gridTemplateColumns: '1fr auto' }}>
            <div className="grid gap-x-6 gap-y-2.5" style={{ gridTemplateColumns: 'repeat(3, minmax(0,1fr))' }}>
              <Field label="Owner age" value={`${sample.ownerAge} yrs`} />
              <Field label="Business credit score" value={sample.businessCreditScore} />
              <Field label="Address tenure" value={`${sample.addressTenureMonths.toFixed(0)} mo`} />
              <Field label="90-day txn count" value={sample.txnCount90d.toLocaleString()} />
              <Field label="Avg txn amount" value={`$${sample.avgTxnAmount.toFixed(2)}`} />
              <Field label="Refund ratio" value={sample.refundRatio.toFixed(3)} />
            </div>
            <div className="flex flex-col items-center justify-center rounded-lg border px-5 py-3" style={{ borderColor: 'var(--red-line)', background: 'var(--red-wash)' }}>
              <div className="text-[length:var(--text-2xs)] font-semibold uppercase" style={{ color: 'var(--red)' }}>fraud probability</div>
              <div className="font-mono text-[length:var(--text-2xl)] font-bold" style={{ color: 'var(--red)' }}>{sample.fraudProbability.toFixed(3)}</div>
              <Pill tone="evaded">EVADED (threshold {mf.threshold})</Pill>
            </div>
          </div>
          <p className="text-[length:var(--text-xs)] mt-3.5" style={{ color: 'var(--muted)' }}>
            Evaded rows cluster near legitimate profiles — long tenure, healthy credit, low refund ratio.
            That resemblance to the legitimate class is exactly what makes them useful as hard negatives.
          </p>
        </Panel>
      )}

      <Panel title="Why the evaded samples matter" tags={<Tag accent="red">the product</Tag>}>
        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(3, minmax(0,1fr))' }}>
          <Step tag="step 1" tone="red" title="Model the minority class">
            CTGAN is trained only on real fraud, so it learns that distribution rather than resampling it. Generated rows are novel, not duplicates.
          </Step>
          <Step tag="step 2" tone="amber" title="Reject the unrealistic">
            Domain constraints filter anything structurally impossible — negative tenure, chargeback ratios above one. Fidelity is enforced, not hoped for.
          </Step>
          <Step tag="step 3" tone="blue" title="Keep only what wins">
            The {mf.evaded} that evaded are realistic, valid, and demonstrably hard for the current model. Folding them back beats thousands of easy samples.
          </Step>
        </div>
      </Panel>
    </>
  )
}

function Field({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-wide" style={{ color: 'var(--muted)' }}>{label}</div>
      <div className="font-mono text-[length:var(--text-base)] font-semibold mt-0.5">{value}</div>
    </div>
  )
}

function Step({ tag, tone, title, children }: { tag: string; tone: 'red' | 'amber' | 'blue'; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border p-3" style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}>
      <div className="flex items-center gap-2 mb-1.5">
        <Tag accent={tone}>{tag}</Tag>
      </div>
      <div className="text-[length:var(--text-sm)] font-semibold mb-1">{title}</div>
      <p className="text-[length:var(--text-xs)]" style={{ color: 'var(--ink-2)' }}>{children}</p>
    </div>
  )
}

function TrainCurveChart({ rows }: { rows: MerchantFraudData['trainCurve'] }) {
  const data = rows.map((r) => ({ name: r.model.replace(' (CTGAN-augmented)', '').replace(' (baseline)', ''), F1: r.f1, 'PR-AUC': r.prAuc }))
  return (
    <div style={{ width: '100%', height: 220 }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 6, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="var(--rule-soft)" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={{ stroke: 'var(--rule)' }} tickLine={false} interval={0} angle={-12} textAnchor="end" height={54} />
          <YAxis domain={[0.75, 1]} tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--rule)', borderRadius: 8, fontSize: 11 }} />
          <Bar dataKey="F1" fill="var(--amber)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="PR-AUC" fill="var(--blue)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function PipelineDiagram({ mf }: { mf: MerchantFraudData }) {
  const stages = [
    { label: 'CTGAN', value: mf.generated.toLocaleString(), sub: 'synthetic fraud', color: 'var(--red)' },
    { label: 'DOMAIN CHECK', value: mf.validTested.toLocaleString(), sub: 'structurally valid', color: 'var(--ink)' },
    { label: 'CLASSIFIER', value: mf.threshold.toFixed(2), sub: 'decision threshold', color: 'var(--blue)' },
  ]
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-0 overflow-x-auto">
        {stages.map((s) => (
          <div key={s.label} className="flex items-center">
            <div className="rounded-lg border px-4 py-3 min-w-[150px] text-center" style={{ borderColor: 'var(--rule)' }}>
              <div className="text-[length:var(--text-xs)] font-semibold" style={{ color: s.color }}>{s.label}</div>
              <div className="font-mono text-[length:var(--text-lg)] font-semibold mt-1" style={{ color: s.color }}>{s.value}</div>
              <div className="text-[length:var(--text-2xs)] mt-0.5" style={{ color: 'var(--muted)' }}>{s.sub}</div>
            </div>
            <svg width="28" height="20" className="shrink-0" aria-hidden="true">
              <line x1="2" y1="10" x2="24" y2="10" stroke="var(--ink-2)" strokeWidth="1.6" markerEnd="url(#mf-ar)" />
              <defs>
                <marker id="mf-ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M0 0 L10 5 L0 10 z" fill="var(--ink-2)" />
                </marker>
              </defs>
            </svg>
          </div>
        ))}
        <div className="flex flex-col gap-2">
          <div className="rounded-lg border px-4 py-2 text-center" style={{ borderColor: 'var(--blue-line)' }}>
            <div className="text-[length:var(--text-2xs)] font-semibold" style={{ color: 'var(--blue)' }}>DETECTED</div>
            <div className="font-mono text-[length:var(--text-base)] font-semibold" style={{ color: 'var(--blue)' }}>{mf.detected.toLocaleString()}</div>
          </div>
          <div className="rounded-lg border px-4 py-2 text-center" style={{ borderColor: 'var(--red-line)' }}>
            <div className="text-[length:var(--text-2xs)] font-semibold" style={{ color: 'var(--red)' }}>EVADED</div>
            <div className="font-mono text-[length:var(--text-base)] font-semibold" style={{ color: 'var(--red)' }}>{mf.evaded}</div>
          </div>
        </div>
      </div>
      <div className="rounded-lg border px-3.5 py-2.5 text-[length:var(--text-xs)]" style={{ borderColor: 'var(--red-line)', background: 'var(--red-wash)', color: 'var(--red)' }}>
        <strong>{mf.evaded} evaded candidates mined as hard negatives</strong> → next training set. The attack makes the defense stronger — that is the loop.
      </div>
    </div>
  )
}
