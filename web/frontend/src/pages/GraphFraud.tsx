import { useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Panel, Tag, MetricCard, Pill, EmptyState } from '../components/ui'
import RunPanel from '../components/RunPanel'
import { Header } from './PromptInjection'
import { useResultsContext } from '../lib/ResultsContext'
import type { GraphFraudData } from '../data/types'

export default function GraphFraud() {
  const { data, refetch } = useResultsContext()
  const gf = data?.graphFraud ?? null

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Graph Fraud · adversarial epochs"
        subtitle="A dual-head heterogeneous graph transformer. Each epoch the red team profiles exactly what was missed and shifts its parameters toward it."
        status={gf ? `${gf.epochs.length} epochs complete` : 'not run yet'}
      />

      <RunPanel
        vector="graph-fraud"
        title="Run the adversarial loop"
        note="local strategist (mock mode) — no Gemini quota used, per the run this repo reports"
        onDone={refetch}
        fields={[
          { key: 'epochs', kind: 'number', label: 'Epochs', defaultValue: 12, min: 1, max: 30 },
        ]}
      />

      {gf ? <Dashboard gf={gf} /> : (
        <EmptyState title="No adversarial run yet" body="Start one above — try 2-3 epochs first to see the loop, since each epoch trains a fresh GNN from scratch." />
      )}
    </div>
  )
}

function Dashboard({ gf }: { gf: GraphFraudData }) {
  const last = gf.epochs[gf.epochs.length - 1]
  const first = gf.epochs[0]
  const [epochIdx, setEpochIdx] = useState(gf.epochs.length - 1)
  const e = gf.epochs[epochIdx]
  const report = gf.evolutionReports[epochIdx]

  return (
    <>
      <Panel
        title="Detector strength across epochs"
        tags={<><Tag accent="blue">node head</Tag><Tag accent="amber">edge head</Tag></>}
        note="mule accounts vs. cross-rail transactions — two different jobs"
      >
        <EpochChart epochs={gf.epochs} />
      </Panel>

      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
        <MetricCard label="Node F1" value={last.node_f1_test.toFixed(3)} accent="blue" trend={{ dir: 'up', text: `from ${first.node_f1_test.toFixed(3)}`, good: true }} sub="mule-account head" />
        <MetricCard label="Edge F1" value={last.edge_f1_test.toFixed(3)} accent="amber" trend={{ dir: 'up', text: `from ${first.edge_f1_test.toFixed(3)}`, good: true }} sub="cross-rail head" />
        <MetricCard label="Combined F1" value={last.combined_f1.toFixed(3)} accent="blue" sub="peak this run" />
        <MetricCard label="Node FPR" value={`${(last.node_fpr_test * 100).toFixed(2)}%`} accent="red" trend={{ dir: 'down', text: `from ${(first.node_fpr_test * 100).toFixed(2)}%`, good: true }} sub="guardrail: 5% ceiling" />
      </div>

      <Panel title="Scrub an epoch" note="drag to replay the adversarial loop, topology by topology">
        <div className="flex flex-col gap-4">
          <input
            type="range"
            min={0}
            max={gf.epochs.length - 1}
            value={epochIdx}
            onChange={(ev) => setEpochIdx(+ev.target.value)}
            className="w-full accent-[var(--blue)]"
          />
          <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <div className="rounded-lg border p-3.5" style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[length:var(--text-base)] font-bold">Epoch {e.epoch}</span>
                {e.node_fpr_test > 0.05 ? <Pill tone="evaded">FPR over guardrail</Pill> : <Pill tone="caught">within guardrail</Pill>}
              </div>
              <div className="font-mono text-[length:var(--text-xs)]" style={{ color: 'var(--muted)' }}>
                topology: {e.topology.split(',').join(', ')}
              </div>
              <div className="font-mono text-[length:var(--text-xs)]" style={{ color: 'var(--muted)' }}>
                dwell: {e.dwell_range}s &middot; mean amount: ${e.amount_mean.toFixed(0)}
              </div>
            </div>
            <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))' }}>
              <MiniStat label="Node F1" value={e.node_f1_test} color="var(--blue)" />
              <MiniStat label="Edge F1" value={e.edge_f1_test} color="var(--amber)" />
              <MiniStat label="Node ASR" value={e.node_asr} color="var(--red)" />
              <MiniStat label="Edge ASR" value={e.edge_asr} color="var(--red)" />
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="The FPR guardrail" note="the false-positive rate is not a passive metric — it drives its own correction">
        <FprChart epochs={gf.epochs} />
        <p className="text-[length:var(--text-xs)] mt-3" style={{ color: 'var(--ink-2)' }}>
          When Node FPR exceeds the 5% industry-tolerable ceiling, the system boosts next-epoch legitimate
          transaction volume by up to 1.5× — specifically penalizing a blue team that hit its F1 target by
          over-flagging.
        </p>
      </Panel>

      {report && (
        <Panel title="Red Team evolution report" tags={<Tag accent="blue">epoch {e.epoch}</Tag>} note="real output from this run, for the scrubbed epoch above">
          <pre
            className="font-mono text-[length:var(--text-2xs)] leading-relaxed overflow-x-auto whitespace-pre"
            style={{ color: 'var(--ink-2)' }}
          >
            {report.trim()}
          </pre>
        </Panel>
      )}
    </>
  )
}

function MiniStat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-lg border px-3 py-2" style={{ borderColor: 'var(--rule-soft)' }}>
      <div className="text-[length:var(--text-2xs)] font-semibold uppercase" style={{ color: 'var(--muted)' }}>{label}</div>
      <div className="font-mono text-[length:var(--text-md)] font-semibold" style={{ color }}>{value.toFixed(3)}</div>
    </div>
  )
}

function EpochChart({ epochs }: { epochs: GraphFraudData['epochs'] }) {
  const data = epochs.map((e) => ({
    epoch: `E${e.epoch}`,
    'Node F1': e.node_f1_test,
    'Edge F1': e.edge_f1_test,
    'Combined F1': e.combined_f1,
  }))
  return (
    <div style={{ width: '100%', height: 240 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="var(--rule-soft)" vertical={false} />
          <XAxis dataKey="epoch" tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={{ stroke: 'var(--rule)' }} tickLine={false} />
          <YAxis domain={[0.65, 1]} tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--rule)', borderRadius: 8, fontSize: 11 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="Node F1" stroke="var(--blue)" strokeWidth={2.4} dot={{ r: 2.5 }} />
          <Line type="monotone" dataKey="Edge F1" stroke="var(--amber)" strokeWidth={2} strokeDasharray="5 3" dot={{ r: 2.5 }} />
          <Line type="monotone" dataKey="Combined F1" stroke="var(--ink-2)" strokeWidth={1.4} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function FprChart({ epochs }: { epochs: GraphFraudData['epochs'] }) {
  const data = epochs.map((e) => ({ epoch: `E${e.epoch}`, 'Node FPR %': +(e.node_fpr_test * 100).toFixed(2) }))
  return (
    <div style={{ width: '100%', height: 160 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="var(--rule-soft)" vertical={false} />
          <XAxis dataKey="epoch" tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={{ stroke: 'var(--rule)' }} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--rule)', borderRadius: 8, fontSize: 11 }} />
          <Line type="monotone" dataKey="Node FPR %" stroke="var(--red)" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
