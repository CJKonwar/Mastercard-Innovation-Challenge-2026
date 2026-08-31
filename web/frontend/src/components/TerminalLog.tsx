import { useEffect, useRef, useState } from 'react'

const TERM = {
  bg: '#0B0E12',
  chrome: '#161A20',
  chromeLine: '#252B34',
  text: '#C7CCD1',
  dim: '#5B6472',
  green: '#4ADE80',
  red: '#F87171',
  amber: '#FBBF24',
  cyan: '#67E8F9',
  bright: '#F3F4F6',
}

// Vector CLI scripts print decorative emoji (✅ 🎯 📊 ⏹️ ...) for a real
// terminal. In this boxed web view they just read as clutter, so strip them
// from what's displayed - lineStyle still runs on the original line below,
// so emoji-based color cues (❌ ⚠ ✅) keep working even once the glyph itself
// is gone from the rendered text.
const EMOJI_SRC = '\\p{Extended_Pictographic}(\\u200D\\p{Extended_Pictographic})*\\uFE0F?'
const EMOJI = new RegExp(EMOJI_SRC, 'gu')
const LEADING_EMOJI = new RegExp(`^(\\s*)(${EMOJI_SRC}\\s*)+`, 'u')
function stripEmoji(line: string): string {
  return line.replace(LEADING_EMOJI, '$1').replace(EMOJI, '')
}

function lineStyle(line: string): { color: string; weight?: number } {
  const t = line.trim()
  if (/^[=\-─]{5,}$/.test(t)) return { color: TERM.dim }
  if (/error|failed|exited with code [^0]|❌|traceback/i.test(t)) return { color: TERM.red, weight: 600 }
  if (/warning|⚠/i.test(t)) return { color: TERM.amber }
  if (/\[ok\]|complete|success|detected:|✅|stopped by user/i.test(t)) return { color: TERM.green }
  if (/^[A-Z][A-Z0-9 /→\-]{3,}$/.test(t) && t.length > 3) return { color: TERM.bright, weight: 700 }
  if (/^(mutation|seed|epoch|round)\s/i.test(t)) return { color: TERM.cyan }
  return { color: TERM.text }
}

export default function TerminalLog({
  command, log, isRunning, status,
}: {
  command: string
  log: string
  isRunning: boolean
  status: 'running' | 'done' | 'failed' | 'stopped'
}) {
  const bodyRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)
  const lines = log ? log.split('\n') : []

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [log])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(log)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable, ignore */
    }
  }

  const dotColor = status === 'running' ? TERM.amber : status === 'done' ? TERM.green : status === 'stopped' ? TERM.amber : TERM.red

  return (
    <div className="mt-3 rounded-lg overflow-hidden border" style={{ borderColor: 'var(--rule)', boxShadow: 'var(--shadow-sm)' }}>
      <div
        className="flex items-center gap-2.5 px-3 py-2"
        style={{ background: TERM.chrome, borderBottom: `1px solid ${TERM.chromeLine}` }}
      >
        <span className="flex gap-1.5 shrink-0">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#EF4444' }} />
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#F59E0B' }} />
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#22C55E' }} />
        </span>
        <span
          className="font-mono text-[length:var(--text-2xs)] truncate flex-1"
          style={{ color: TERM.dim }}
          title={command}
        >
          $ {command}
        </span>
        <span className="w-2 h-2 rounded-full shrink-0" style={{ background: dotColor, boxShadow: isRunning ? `0 0 6px ${dotColor}` : 'none' }} />
        <button
          onClick={copy}
          className="font-mono text-[length:var(--text-2xs)] px-2 py-0.5 rounded shrink-0 transition-colors"
          style={{ color: TERM.dim, border: `1px solid ${TERM.chromeLine}` }}
        >
          {copied ? 'copied' : 'copy'}
        </button>
      </div>
      <div
        ref={bodyRef}
        className="font-mono text-[length:var(--text-2xs)] leading-relaxed overflow-y-auto px-3.5 py-3"
        style={{ background: TERM.bg, maxHeight: 260 }}
      >
        {lines.length === 0 ? (
          <span style={{ color: TERM.dim }}>waiting for output…</span>
        ) : (
          lines.map((line, i) => {
            const s = lineStyle(line)
            const clean = stripEmoji(line)
            return (
              <div key={i} style={{ color: s.color, fontWeight: s.weight, whiteSpace: 'pre-wrap' }}>
                {clean || ' '}
              </div>
            )
          })
        )}
        {isRunning && (
          <span className="inline-block w-[7px] h-[13px] align-middle ml-0.5 animate-pulse" style={{ background: TERM.green }} />
        )}
      </div>
    </div>
  )
}
