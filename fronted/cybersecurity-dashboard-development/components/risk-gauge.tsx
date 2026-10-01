'use client'

import { useEffect, useState } from 'react'
import { threatFromScore, threatMeta, type Infringement } from '@/lib/data'

const SIZE = 220
const STROKE = 16
const RADIUS = (SIZE - STROKE) / 2
const CIRC = 2 * Math.PI * RADIUS
// 3/4 circle gauge (270 degrees)
const ARC = 0.75

export function RiskGauge({
  score = 0,
  listings = [],
}: {
  score?: number
  listings?: Infringement[]
}) {
  const [animated, setAnimated] = useState(0)

  useEffect(() => {
    const t = requestAnimationFrame(() => setAnimated(score))
    return () => cancelAnimationFrame(t)
  }, [score])

  const level = threatFromScore(score)
  const meta = threatMeta[level]
  const gaugeColor =
    level === 'critical'
      ? 'var(--danger)'
      : level === 'elevated'
        ? 'oklch(0.7 0.18 45)'
        : level === 'moderate'
          ? 'var(--warning)'
          : 'var(--success)'

  const dash = CIRC * ARC
  const offset = dash - (animated / 100) * dash

  const critical = listings.filter((l) => l.fraudScore >= 80).length
  const elevated = listings.filter((l) => l.fraudScore >= 60 && l.fraudScore < 80).length
  const moderate = listings.filter((l) => l.fraudScore >= 35 && l.fraudScore < 60).length

  return (
    <section
      aria-label="Aggregate risk score"
      className="flex h-full flex-col rounded-xl border border-border bg-card p-5"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Aggregate Risk Score</h2>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${meta.bg} ${meta.text} ${meta.ring}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
          {meta.label} Threat
        </span>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center py-4">
        <div className="relative" style={{ width: SIZE, height: SIZE * 0.82 }}>
          <svg
            width={SIZE}
            height={SIZE}
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            className="-rotate-[225deg]"
            role="img"
            aria-label={`Risk score ${score} out of 100, ${meta.label} threat`}
          >
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              stroke="var(--secondary)"
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${CIRC}`}
            />
            <circle
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              stroke={gaugeColor}
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${CIRC}`}
              strokeDashoffset={offset}
              style={{
                transition: 'stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1)',
                filter: `drop-shadow(0 0 6px ${gaugeColor})`,
              }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="font-mono text-5xl font-bold tabular-nums"
              style={{ color: gaugeColor }}
            >
              {Math.round(animated)}
            </span>
            <span className="text-xs text-muted-foreground">/ 100 risk index</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 border-t border-border pt-4 text-center">
        <div>
          <p className="font-mono text-sm font-semibold text-[var(--danger)]">{critical}</p>
          <p className="text-[11px] text-muted-foreground">Critical</p>
        </div>
        <div>
          <p className="font-mono text-sm font-semibold text-orange-400">{elevated}</p>
          <p className="text-[11px] text-muted-foreground">Elevated</p>
        </div>
        <div>
          <p className="font-mono text-sm font-semibold text-[var(--warning)]">{moderate}</p>
          <p className="text-[11px] text-muted-foreground">Moderate</p>
        </div>
      </div>
    </section>
  )
}
