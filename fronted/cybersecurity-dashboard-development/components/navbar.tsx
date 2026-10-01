'use client'

import { useEffect, useState } from 'react'
import { ShieldCheck, Zap } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'

type Credits = {
  total_searches_left: number | null
  searches_per_month: number | null
}

export function Navbar() {
  const [credits, setCredits] = useState<Credits | null>(null)
  const [online, setOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      const [health, creds] = await Promise.allSettled([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/api/credits`),
      ])
      if (cancelled) return

      setOnline(health.status === 'fulfilled' && health.value.ok)

      if (creds.status === 'fulfilled' && creds.value.ok) {
        try {
          setCredits(await creds.value.json())
          return
        } catch {
          // fall through to "unknown"
        }
      }
      setCredits(null)
    }

    load()
    const id = setInterval(load, 10000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  const left = credits?.total_searches_left
  const total = credits?.searches_per_month

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/30">
            <ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" />
            <span
              className={`absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full ring-2 ring-background ${
                online === false ? 'bg-[var(--danger)]' : 'bg-[var(--success)]'
              }`}
            />
          </div>
          <div className="leading-tight">
            <p className="font-semibold tracking-tight">
              IP-Sentinel <span className="text-primary">AI</span>
            </p>
            <p className="text-[11px] text-muted-foreground">
              Intellectual Property Threat Intelligence
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <div className="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 sm:flex">
            <span className="relative flex h-2 w-2">
              {online !== false && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--success)] opacity-60" />
              )}
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  online === false ? 'bg-[var(--danger)]' : 'bg-[var(--success)]'
                }`}
              />
            </span>
            <span className="text-xs font-medium text-muted-foreground">
              System Status:{' '}
              {online === false ? (
                <span className="text-[var(--danger)]">Backend offline</span>
              ) : online === null ? (
                <span>Checking…</span>
              ) : (
                <span className="text-[var(--success)]">Operational</span>
              )}
            </span>
          </div>

          <div
            className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5"
            title="Live SerpApi searches remaining this month"
          >
            <Zap className="h-3.5 w-3.5 text-[var(--warning)]" aria-hidden="true" />
            <span className="font-mono text-xs font-semibold tabular-nums">
              {left != null ? left.toLocaleString() : '—'}
              {left != null && total != null ? ` / ${total.toLocaleString()}` : ''}
            </span>
            <span className="hidden text-xs text-muted-foreground sm:inline">
              credits
            </span>
          </div>

          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground ring-1 ring-border">
            AC
          </div>
        </div>
      </div>
    </header>
  )
}
