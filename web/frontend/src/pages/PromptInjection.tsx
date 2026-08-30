import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Panel, Tag, MetricCard, ListCard, Field, StatusPill, EmptyState } from '../components/ui'
import RunPanel from '../components/RunPanel'
import { useResultsContext } from '../lib/ResultsContext'
import type { PromptInjectionData } from '../data/types'
import type { Accent } from '../data'

const TECHNIQUE_LABEL: Record<string, string> = {
  t0_naive_imperative: 'T0 — naive imperative',
  t1_authority_spoof: 'T1 — authority spoof',
  t2_obfuscation: 'T2 — obfuscation',
  t3_semantic_lie: 'T3 — semantic lie',
  t4_multihop_split: 'T4 — multi-hop split',
  t5_adaptive: 'T5 — adaptive evasion',
}

export default function PromptInjection() {
  const { data, refetch } = useResultsContext()
  const pi = data?.promptInjection ?? null

  return (
    <div className="flex flex-col gap-5">
      <Header
        title="Prompt Injection · closed loop"
        subtitle="Each round the attacker evolves against the current defense; the defense then retrains on whatever beat it."
        status={pi ? `${pi.history.length} round${pi.history.length === 1 ? '' : 's'} recorded` : 'not run yet'}
        accent="red"
      />

      <RunPanel
        vector="prompt-injection"
        title="Run the closed loop"
        accent="red"
        onDone={refetch}
        fields={[
          { key: 'rounds', kind: 'number', label: 'Rounds', defaultValue: 3, min: 1, max: 10 },
          { key: 'budget', kind: 'number', label: 'Mutations / round', defaultValue: 20, min: 1, max: 100 },
        ]}
      />

      {pi ? <Dashboard pi={pi} /> : (
        <EmptyState
          title="No archive yet"
          body="Start a run above — a single round with a small budget (try 1 round × 5) is enough to see the loop work end to end."
        />
      )}
    </div>
  )
}

function Dashboard({ pi }: { pi: PromptInjectionData }) {
  const last = pi.history[pi.history.length - 1]

  const surfaces = useMemo(() => Array.from(new Set(pi.allElites.map((e) => e.surface))).sort(), [pi])
  const objectives = useMemo(() => Array.from(new Set(pi.allElites.map((e) => e.objective))).sort(), [pi])
  const techniques = useMemo(() => Array.from(new Set(pi.allElites.map((e) => e.technique))).sort(), [pi])

  const [surface, setSurface] = useState(surfaces[0])
  const [technique, setTechnique] = useState(techniques[0])
  const [objective, setObjective] = useState(objectives[0])

  const activeSurface = surfaces.includes(surface) ? surface : surfaces[0]
  const activeTechnique = techniques.includes(technique) ? technique : techniques[0]
  const activeObjective = objectives.includes(objective) ? objective : objectives[0]

  const matches = pi.allElites.filter(
    (e) => e.surface === activeSurface && e.technique === activeTechnique && e.objective === activeObjective,
  )
  const otherTechniques = pi.allElites.filter((e) => e.surface === activeSurface && e.objective === activeObjective)

  return (
    <>
      <Panel
        title="The loop"
        tags={<><Tag accent="red">red</Tag><Tag accent="blue">blue</Tag></>}
        accent="red"
      >
        <LoopDiagram archiveSize={pi.archiveSize} totalCells={pi.totalCells} />
      </Panel>

      {last && (
        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(4, minmax(0,1fr))' }}>
          <MetricCard label="Mutation ASR" value={`${(last.mutationAsr * 100).toFixed(0)}%`} accent="red" sub="evolving attacks — the arms race" />
          <MetricCard label="Detection" value={`${(last.mutationDetection * 100).toFixed(0)}%`} accent="blue" sub="step-up or block" />
          <MetricCard label="Archive coverage" value={<>{last.coverage}<span className="text-[length:var(--text-md)]" style={{ color: 'var(--muted)' }}> / {last.totalCells}</span></>} accent="amber" sub="niches claimed" />
          <MetricCard label="Mean fitness" value={last.meanFitness.toFixed(3)} accent="blue" sub="red-team reward" />
        </div>
      )}

      {pi.history.length > 1 && (
        <Panel title="Metrics by round" note="seed ASR uses a fixed set — movement there is purely the defense" accent="red">
          <RoundChart history={pi.history} />
        </Panel>
      )}

      <Panel
        title="Try an attack configuration"
        note="real archive data — every result below actually ran against the target agent"
        accent="red"
      >
        <div className="flex flex-wrap gap-3 mb-4">
          <Field label="Surface" value={activeSurface} onChange={setSurface} options={surfaces.map((s) => ({ value: s, label: s.replace(/_/g, ' ') }))} />
          <Field label="Technique" value={activeTechnique} onChange={setTechnique} options={techniques.map((t) => ({ value: t, label: TECHNIQUE_LABEL[t] ?? t }))} />
          <Field label="Objective" value={activeObjective} onChange={setObjective} options={objectives.map((o) => ({ value: o, label: o.replace(/_/g, ' ') }))} />
        </div>

        {matches.length > 0 ? (
          <div className="flex flex-col gap-3">
            {matches.map((e, i) => (
              <ListCard key={i}>
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <Tag accent="red">fitness {e.fitness.toFixed(3)}</Tag>
                  <span className="font-mono text-[length:var(--text-xs)]" style={{ color: 'var(--ink-2)' }}>
                    {e.surface} &middot; {TECHNIQUE_LABEL[e.technique] ?? e.technique} &middot; {e.objective}
                  </span>
                </div>
                <p className="font-mono text-[length:var(--text-sm)] leading-relaxed" style={{ color: 'var(--ink)' }}>&ldquo;{e.text}&rdquo;</p>
                {e.targetSpec && Object.keys(e.targetSpec).length > 0 && (
                  <div className="mt-2 text-[length:var(--text-xs)] font-mono" style={{ color: 'var(--ink-2)' }}>
                    target: {Object.entries(e.targetSpec).map(([k, v]) => `${k}=${v}`).join(', ')}
                  </div>
                )}
              </ListCard>
            ))}
          </div>
        ) : (
          <div className="text-[length:var(--text-sm)] rounded-lg border px-3.5 py-4 leading-relaxed" style={{ borderColor: 'var(--rule-soft)', color: 'var(--ink-2)', background: 'var(--surface-2)' }}>
            No elite claimed this exact niche yet — MAP-Elites only keeps a cell once something wins it.
            {otherTechniques.length > 0 && (
              <> This surface/objective pair <em>is</em> covered by other techniques: {otherTechniques.map((e) => TECHNIQUE_LABEL[e.technique] ?? e.technique).join(', ')}.</>
            )}
          </div>
        )}
      </Panel>

      <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <Panel title="Technique distribution" note={`${pi.archiveSize} elites`} accent="red">
          <BreakdownBars counts={pi.techniqueCounts} labelMap={TECHNIQUE_LABEL} total={pi.archiveSize} />
        </Panel>
        <Panel title="Top elites by fitness" note="highest-reward payloads this archive" accent="red">
          <div className="flex flex-col max-h-[280px] overflow-y-auto">
            {pi.sampleElites.slice(0, 8).map((e, i) => (
              <div key={i} className="grid gap-2 items-center py-1.75 border-b font-mono text-[length:var(--text-xs)]" style={{ borderColor: 'var(--rule-soft)', gridTemplateColumns: '44px 1fr auto' }}>
                <span style={{ color: 'var(--faint)' }}>{e.fitness.toFixed(2)}</span>
                <span className="truncate" style={{ color: 'var(--ink-2)' }}>{e.technique.replace('t', 'T').split('_')[0]} → {e.surface} → {e.objective}</span>
                <StatusPill live={false}>{e.technique.startsWith('t0') ? 'T0' : e.technique.slice(0, 2).toUpperCase()}</StatusPill>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  )
}

export function Header({
  title, subtitle, status, accent = 'ink',
}: {
  title: string
  subtitle: string
  status: string
  accent?: Accent | 'ink'
}) {
  const color = accent === 'ink' ? 'var(--ink)' : `var(--${accent})`
  return (
    <div
      className="relative overflow-hidden rounded-xl border pl-6 pr-5 py-4.5 flex items-start justify-between gap-4 flex-wrap"
      style={{ background: 'var(--surface)', borderColor: 'var(--rule)', boxShadow: 'var(--shadow-sm)' }}
    >
      <span className="absolute left-0 top-0 bottom-0 w-1.5" style={{ background: color }} />
      <div className="min-w-0">
        <h1 className="text-[length:var(--text-2xl)] font-extrabold tracking-tight leading-tight">{title}</h1>
        <div
          className="flex items-start gap-2.5 mt-3 rounded-lg px-3.5 py-2.5 max-w-[68ch]"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--rule-soft)' }}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <p className="text-[length:var(--text-sm)] leading-relaxed" style={{ color: 'var(--ink-2)' }}>{subtitle}</p>
        </div>
      </div>
      <StatusPill live={false}>{status}</StatusPill>
    </div>
  )
}

function BreakdownBars({ counts, labelMap, total }: { counts: Record<string, number>; labelMap: Record<string, string>; total: number }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1])
  return (
    <div className="flex flex-col gap-2.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-2.5">
          <span className="font-mono text-[length:var(--text-xs)] w-[144px] shrink-0 truncate" style={{ color: 'var(--ink-2)' }}>{labelMap[k] ?? k}</span>
          <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--sunk)' }}>
            <div className="h-full rounded-full" style={{ width: `${(v / total) * 100}%`, background: 'var(--red)', opacity: 0.75 }} />
          </div>
          <span className="font-mono text-[length:var(--text-xs)] w-10 text-right" style={{ color: 'var(--muted)' }}>{v}</span>
        </div>
      ))}
    </div>
  )
}

function LoopDiagram({ archiveSize, totalCells }: { archiveSize: number; totalCells: number }) {
  const stages = [
    {
      n: '1', label: 'Generate', color: 'var(--red)', wash: 'var(--red-wash)',
      desc: 'Red team breeds new attack payloads from the archive’s fittest niches.',
    },
    {
      n: '2', label: 'Simulate', color: 'var(--ink-2)', wash: 'var(--sunk)',
      desc: 'The Qwen3-8B target agent handles the payload live, as it would in production.',
    },
    {
      n: '3', label: 'Detect', color: 'var(--blue)', wash: 'var(--blue-wash)',
      desc: 'Three deterministic tiers fuse into one score — content rules, a provenance graph, then a delegated-scope check.',
    },
    {
      n: '4', label: 'Judge', color: 'var(--amber)', wash: 'var(--amber-wash)',
      desc: 'Ground truth is checked: did the payment actually move to the attacker?',
    },
    {
      n: '5', label: 'Retrain', color: 'var(--blue)', wash: 'var(--blue-wash)',
      desc: 'Blue team retrains on every payload that beat it — today’s win is tomorrow’s hard negative.',
    },
  ]
  return (
    <div>
      <div className="grid gap-0" style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0,1fr))` }}>
        {stages.map((s, i) => (
          <div key={s.n} className="flex items-stretch min-w-0">
            <div
              className="rounded-xl border px-4.5 py-4 flex-1 min-w-0 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
              style={{ borderColor: 'var(--rule)', background: 'var(--surface)', boxShadow: 'var(--shadow-sm)' }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span
                  className="flex items-center justify-center w-6 h-6 rounded-full text-[length:var(--text-xs)] font-bold shrink-0"
                  style={{ background: s.wash, color: s.color }}
                >
                  {s.n}
                </span>
                <span className="text-[length:var(--text-md)] font-bold" style={{ color: s.color }}>{s.label}</span>
              </div>
              <p className="text-[length:var(--text-xs)] leading-relaxed" style={{ color: 'var(--muted)' }}>{s.desc}</p>
            </div>
            {i < stages.length - 1 && (
              <div className="flex items-center justify-center w-8 shrink-0">
                <svg width="24" height="20" aria-hidden="true">
                  <line
                    x1="2" y1="10" x2="20" y2="10"
                    stroke={stages[i + 1].color} strokeOpacity="0.6" strokeWidth="2"
                    strokeDasharray="1 5" strokeLinecap="round"
                    className="flow-line" markerEnd="url(#pi-ar)"
                  />
                  <defs>
                    <marker id="pi-ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                      <path d="M0 0 L10 5 L0 10 z" fill={stages[i + 1].color} opacity="0.6" />
                    </marker>
                  </defs>
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2.5 mt-3 pt-3 border-t" style={{ borderColor: 'var(--rule-soft)' }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 spin-slow">
          <path d="M23 4v6h-6" />
          <path d="M1 20v-6h6" />
          <path d="M3.51 9a9 9 0 0114.13-3.36L23 10M1 14l5.36 4.36A9 9 0 0020.49 15" />
        </svg>
        <p className="text-[length:var(--text-xs)] leading-relaxed" style={{ color: 'var(--muted)' }}>
          Stage 5 loops back into Stage 1 — the retrained defense faces the next round’s mutations. So far it has claimed{' '}
          <span className="font-mono font-semibold" style={{ color: 'var(--blue)' }}>{archiveSize}/{totalCells}</span> niches in the archive.
        </p>
      </div>
    </div>
  )
}

function RoundChart({ history }: { history: PromptInjectionData['history'] }) {
  const data = history.map((h) => ({
    round: `R${h.round}`,
    'Seed ASR': +(h.seedAsr * 100).toFixed(1),
    'Mutation ASR': +(h.mutationAsr * 100).toFixed(1),
    'Detection': +(h.mutationDetection * 100).toFixed(1),
  }))
  return (
    <div style={{ width: '100%', height: 220 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 12, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="var(--rule-soft)" vertical={false} />
          <XAxis dataKey="round" tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={{ stroke: 'var(--rule)' }} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} unit="%" />
          <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--rule)', borderRadius: 8, fontSize: 11 }} />
          <Line type="monotone" dataKey="Seed ASR" stroke="var(--red)" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Mutation ASR" stroke="var(--amber)" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Detection" stroke="var(--blue)" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
