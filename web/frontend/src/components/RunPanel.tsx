import { useState } from 'react'
import { Panel, StatusPill } from './ui'
import TerminalLog from './TerminalLog'
import { useJob } from '../lib/useJob'
import type { Accent } from '../data'

export type RunField =
  | { key: string; kind: 'number'; label: string; defaultValue: number; min: number; max: number; help?: string }
  | { key: string; kind: 'checkbox'; label: string; defaultValue: boolean; help?: string }

export default function RunPanel({
  vector, title, fields, onDone, note, accent = 'ink',
}: {
  vector: string
  title: string
  fields: RunField[]
  onDone: () => void
  note?: string
  accent?: Accent | 'ink'
}) {
  const buttonColor = accent === 'ink' ? 'var(--ink)' : `var(--${accent})`
  const { job, run, stop, starting, stopping, error, isRunning } = useJob(vector, onDone)
  const [values, setValues] = useState<Record<string, number | boolean>>(() =>
    Object.fromEntries(fields.map((f) => [f.key, f.defaultValue])),
  )

  const set = (key: string, v: number | boolean) => setValues((s) => ({ ...s, [key]: v }))

  const hasEmptyNumber = fields.some((f) => f.kind === 'number' && !(values[f.key] as number))

  return (
    <Panel title={title} note={note} accent={accent}>
      <div className="flex flex-wrap items-end gap-3.5">
        {fields.map((f) => (
          <label key={f.key} className="flex flex-col gap-1 text-[length:var(--text-sm)]" style={{ color: 'var(--ink-2)' }}>
            <span className="eyebrow" title={f.help}>{f.label}</span>
            {f.kind === 'number' ? (
              <input
                type="number"
                min={f.min}
                max={f.max}
                value={values[f.key] as number === 0 ? '' : (values[f.key] as number)}
                disabled={isRunning}
                onChange={(e) => {
                  const raw = e.target.value
                  if (raw === '') { set(f.key, 0); return }
                  const n = +raw
                  if (Number.isNaN(n)) return
                  set(f.key, Math.min(f.max, Math.max(0, n)))
                }}
                onBlur={(e) => {
                  const n = +e.target.value || 0
                  if (n < f.min) set(f.key, f.min)
                }}
                className="w-24 rounded-md border px-2.5 py-1.5 text-[length:var(--text-base)] font-mono outline-none disabled:opacity-50"
                style={{ background: 'var(--surface)', borderColor: 'var(--rule)', color: 'var(--ink)' }}
              />
            ) : (
              <label className="flex items-center gap-1.5 h-[30px] text-[length:var(--text-sm)]">
                <input
                  type="checkbox"
                  checked={values[f.key] as boolean}
                  disabled={isRunning}
                  onChange={(e) => set(f.key, e.target.checked)}
                  className="accent-[var(--blue)]"
                />
                {f.help}
              </label>
            )}
          </label>
        ))}
        <button
          onClick={() => run(values)}
          disabled={isRunning || starting || hasEmptyNumber}
          className="rounded-md px-4 py-2 text-[length:var(--text-sm)] font-semibold text-white transition-opacity disabled:opacity-50"
          style={{ background: buttonColor }}
        >
          {isRunning ? 'Running…' : starting ? 'Starting…' : 'Start run'}
        </button>
        {isRunning && (
          <button
            onClick={() => stop()}
            disabled={stopping}
            className="rounded-md px-4 py-2 text-[length:var(--text-sm)] font-semibold border transition-opacity disabled:opacity-50"
            style={{ borderColor: 'var(--red-line)', color: 'var(--red)', background: 'var(--red-wash)' }}
          >
            {stopping ? 'Stopping…' : 'Stop'}
          </button>
        )}
        {job && (
          <StatusPill live={isRunning}>
            {isRunning ? 'in progress'
              : job.status === 'done' ? 'completed'
              : job.status === 'stopped' ? 'stopped'
              : 'failed'}
          </StatusPill>
        )}
      </div>

      {error && (
        <div className="mt-3 rounded-lg border px-3 py-2 text-[length:var(--text-sm)]" style={{ borderColor: 'var(--red-line)', background: 'var(--red-wash)', color: 'var(--red)' }}>
          {error}
        </div>
      )}

      {job && (
        <TerminalLog command={job.command} log={job.log} isRunning={isRunning} status={job.status} />
      )}
    </Panel>
  )
}
