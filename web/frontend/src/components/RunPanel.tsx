import { useEffect, useRef, useState } from 'react'
import { Panel, StatusPill } from './ui'
import { useJob } from '../lib/useJob'

export type RunField =
  | { key: string; kind: 'number'; label: string; defaultValue: number; min: number; max: number; help?: string }
  | { key: string; kind: 'checkbox'; label: string; defaultValue: boolean; help?: string }

export default function RunPanel({
  vector, title, fields, onDone, note,
}: {
  vector: string
  title: string
  fields: RunField[]
  onDone: () => void
  note?: string
}) {
  const { job, run, stop, starting, stopping, error, isRunning } = useJob(vector, onDone)
  const [values, setValues] = useState<Record<string, number | boolean>>(() =>
    Object.fromEntries(fields.map((f) => [f.key, f.defaultValue])),
  )
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [job?.log])

  const set = (key: string, v: number | boolean) => setValues((s) => ({ ...s, [key]: v }))

  return (
    <Panel title={title} note={note}>
      <div className="flex flex-wrap items-end gap-3.5">
        {fields.map((f) => (
          <label key={f.key} className="flex flex-col gap-1 text-[length:var(--text-sm)]" style={{ color: 'var(--ink-2)' }}>
            <span className="eyebrow" title={f.help}>{f.label}</span>
            {f.kind === 'number' ? (
              <input
                type="number"
                min={f.min}
                max={f.max}
                value={values[f.key] as number}
                disabled={isRunning}
                onChange={(e) => set(f.key, Math.min(f.max, Math.max(f.min, +e.target.value || f.min)))}
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
          disabled={isRunning || starting}
          className="rounded-md px-4 py-2 text-[length:var(--text-sm)] font-semibold text-white transition-opacity disabled:opacity-50"
          style={{ background: 'var(--ink)' }}
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
        <div
          ref={logRef}
          className="mt-3 rounded-lg border p-3 font-mono text-[length:var(--text-2xs)] leading-relaxed overflow-y-auto whitespace-pre-wrap"
          style={{ borderColor: 'var(--rule-soft)', background: 'var(--sunk)', color: 'var(--ink-2)', maxHeight: 220 }}
        >
          {job.log || 'waiting for output…'}
          {job.status === 'failed' && (
            <div className="mt-1 font-semibold" style={{ color: 'var(--red)' }}>
              exited with code {job.returncode}
            </div>
          )}
          {job.status === 'stopped' && (
            <div className="mt-1 font-semibold" style={{ color: 'var(--amber)' }}>
              stopped by user
            </div>
          )}
        </div>
      )}
    </Panel>
  )
}
