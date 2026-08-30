import { useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Panel, Tag, MetricCard, ListCard, Pill, EmptyState } from '../components/ui'
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
        accent="violet"
      />

      <RunPanel
        vector="graph-fraud"
        title="Run the adversarial loop"
        note="local strategist (mock mode) — no Gemini quota used, per the run this repo reports"
        accent="violet"
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
        accent="violet"
      >
        <EpochChart epochs={gf.epochs} />
      </Panel>

      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
        <MetricCard label="Node F1" value={last.node_f1_test.toFixed(3)} accent="blue" trend={{ dir: 'up', text: `from ${first.node_f1_test.toFixed(3)}`, good: true }} sub="mule-account head" />
        <MetricCard label="Edge F1" value={last.edge_f1_test.toFixed(3)} accent="amber" trend={{ dir: 'up', text: `from ${first.edge_f1_test.toFixed(3)}`, good: true }} sub="cross-rail head" />
        <MetricCard label="Combined F1" value={last.combined_f1.toFixed(3)} accent="blue" sub="peak this run" />
        <MetricCard label="Node FPR" value={`${(last.node_fpr_test * 100).toFixed(2)}%`} accent="red" trend={{ dir: 'down', text: `from ${(first.node_fpr_test * 100).toFixed(2)}%`, good: true }} sub="guardrail: 5% ceiling" />
      </div>

      <Panel title="Scrub an epoch" note="click an epoch to replay the adversarial loop, topology by topology" accent="violet">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            {gf.epochs.map((ep, i) => {
              const isActive = i === epochIdx
              const overGuardrail = ep.node_fpr_test > 0.05
              return (
                <button
                  key={ep.epoch}
                  onClick={() => setEpochIdx(i)}
                  className="shrink-0 flex flex-col items-center gap-1.5 rounded-lg border px-3.25 py-2 transition-all duration-150 hover:-translate-y-0.5"
                  style={{
                    borderColor: isActive ? 'var(--blue-line)' : 'var(--rule)',
                    background: isActive ? 'var(--blue-wash)' : 'var(--surface)',
                    boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                  }}
                >
                  <span className="font-mono text-[length:var(--text-sm)] font-bold" style={{ color: isActive ? 'var(--blue)' : 'var(--ink-2)' }}>
                    {ep.epoch}
                  </span>
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: overGuardrail ? 'var(--red)' : 'var(--blue)', opacity: isActive ? 1 : 0.4 }}
                  />
                </button>
              )
            })}
          </div>
          <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <ListCard>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[length:var(--text-base)] font-bold">Epoch {e.epoch}</span>
                {e.node_fpr_test > 0.05 ? <Pill tone="evaded">FPR over guardrail</Pill> : <Pill tone="caught">within guardrail</Pill>}
              </div>
              <div className="font-mono text-[length:var(--text-xs)]" style={{ color: 'var(--ink-2)' }}>
                topology: {e.topology.split(',').join(', ')}
              </div>
              <div className="font-mono text-[length:var(--text-xs)] mt-0.5" style={{ color: 'var(--ink-2)' }}>
                dwell: {e.dwell_range}s &middot; mean amount: ${e.amount_mean.toFixed(0)}
              </div>
            </ListCard>
            <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))' }}>
              <MiniStat label="Node F1" value={e.node_f1_test} color="var(--blue)" />
              <MiniStat label="Edge F1" value={e.edge_f1_test} color="var(--amber)" />
              <MiniStat label="Node ASR" value={e.node_asr} color="var(--red)" />
              <MiniStat label="Edge ASR" value={e.edge_asr} color="var(--red)" />
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="The FPR guardrail" note="the false-positive rate is not a passive metric — it drives its own correction" accent="violet">
        <FprChart epochs={gf.epochs} />
        <p className="text-[length:var(--text-xs)] mt-3" style={{ color: 'var(--ink-2)' }}>
          When Node FPR exceeds the 5% industry-tolerable ceiling, the system boosts next-epoch legitimate
          transaction volume by up to 1.5× — specifically penalizing a blue team that hit its F1 target by
          over-flagging.
        </p>
      </Panel>

      {report && (
        <Panel title="Red Team evolution report" tags={<Tag accent="blue">epoch {e.epoch}</Tag>} note="real output from this run, for the scrubbed epoch above" accent="violet">
          <EvolutionReport report={report} />
        </Panel>
      )}
    </>
  )
}

interface BlindSpot {
  feature: string
  caughtMean: number
  missedMean: number
  shift: number
  direction: 'increase' | 'decrease'
}

function parseEvolutionReport(raw: string): { spots: BlindSpot[]; noBlindSpots: boolean } {
  if (raw.includes('No blind spots found')) return { spots: [], noBlindSpots: true }
  const spots: BlindSpot[] = []
  const re = /📌\s*(\S+):\s*\n\s*Caught fraud mean:\s*([\d.]+)\s*\n\s*Missed fraud mean:\s*([\d.]+)\s*\n\s*Shift:\s*([+-][\d.]+)\s*\((\w+)\)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(raw))) {
    spots.push({
      feature: m[1],
      caughtMean: parseFloat(m[2]),
      missedMean: parseFloat(m[3]),
      shift: parseFloat(m[4]),
      direction: m[5] as 'increase' | 'decrease',
    })
  }
  return { spots, noBlindSpots: false }
}

function EvolutionReport({ report }: { report: string }) {
  const { spots, noBlindSpots } = parseEvolutionReport(report)

  if (noBlindSpots) {
    return (
      <div className="rounded-lg border px-4 py-3.5 text-[length:var(--text-sm)]" style={{ borderColor: 'var(--blue-line)', background: 'var(--blue-wash)', color: 'var(--ink-2)' }}>
        <span className="font-semibold" style={{ color: 'var(--blue)' }}>No blind spots found —</span> the blue team caught everything this epoch. The red team will try a completely different topology next round.
      </div>
    )
  }

  if (spots.length === 0) {
    // Format didn't match what this component expects — fall back to raw output rather than lose it.
    return (
      <pre className="font-mono text-[length:var(--text-2xs)] leading-relaxed overflow-x-auto whitespace-pre" style={{ color: 'var(--ink-2)' }}>
        {report.trim()}
      </pre>
    )
  }

  return (
    <div className="flex flex-col gap-3.5">
      <p className="text-[length:var(--text-sm)]" style={{ color: 'var(--ink-2)' }}>
        <span className="font-mono font-bold" style={{ color: 'var(--red)' }}>{spots.length}</span> blind spot{spots.length === 1 ? '' : 's'} the blue team missed this epoch — the red team steers its next mutations toward these.
      </p>
      <div className="grid gap-3.5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        {spots.map((s) => {
          const maxVal = Math.max(s.caughtMean, s.missedMean, 0.0001)
          const up = s.direction === 'increase'
          return (
            <div key={s.feature} className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--rule)' }}>
              <div className="flex items-center justify-between gap-2 px-3.5 py-2.5 border-b" style={{ borderColor: 'var(--rule-soft)', background: 'var(--surface-2)' }}>
                <span className="font-mono text-[length:var(--text-sm)] font-bold">{s.feature}</span>
                <span
                  className="font-mono text-[length:var(--text-xs)] font-bold px-1.75 py-0.5 rounded-full"
                  style={{ color: up ? 'var(--blue)' : 'var(--red)', background: up ? 'var(--blue-wash)' : 'var(--red-wash)' }}
                >
                  {up ? '↑' : '↓'} {s.shift > 0 ? '+' : ''}{s.shift.toFixed(4)}
                </span>
              </div>
              <div className="px-3.5 py-3.5 flex flex-col gap-2.5">
                <StatBar label="Caught fraud mean" value={s.caughtMean} max={maxVal} color="var(--blue)" />
                <StatBar label="Missed fraud mean" value={s.missedMean} max={maxVal} color="var(--red)" />
                <div className="text-[length:var(--text-xs)] rounded-lg px-2.75 py-2 mt-0.5" style={{ background: 'var(--sunk)', color: 'var(--ink-2)' }}>
                  → Red team will <strong>{s.direction}</strong> this parameter next epoch
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function StatBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="text-[length:var(--text-xs)] w-[136px] shrink-0" style={{ color: 'var(--ink-2)' }}>{label}</span>
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--sunk)' }}>
        <div className="h-full rounded-full" style={{ width: `${Math.max(4, (value / max) * 100)}%`, background: color }} />
      </div>
      <span className="font-mono text-[length:var(--text-xs)] w-16 text-right font-semibold">{value.toFixed(4)}</span>
    </div>
  )
}

function MiniStat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-xl border px-3.5 py-2.5" style={{ borderColor: 'var(--rule-soft)' }}>
      <div className="text-[length:var(--text-xs)] font-bold uppercase tracking-wide" style={{ color: 'var(--muted)' }}>{label}</div>
      <div className="font-mono text-[length:var(--text-md)] font-semibold mt-0.5" style={{ color }}>{value.toFixed(3)}</div>
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
