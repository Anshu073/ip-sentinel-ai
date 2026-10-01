import type { LucideIcon } from 'lucide-react'
import { AlertTriangle, Database, ShieldAlert, TrendingDown } from 'lucide-react'
import type { BackendScanResponse } from '@/lib/api'

type Stat = {
  label: string
  value: string
  sub: string
  trend: string
  trendUp: boolean
  icon: LucideIcon
  tone: string
  toneBg: string
}

function threatLabel(score: number) {
  if (score >= 80) return 'Critical'
  if (score >= 60) return 'Elevated'
  if (score >= 35) return 'Moderate'
  return 'Low'
}

export function StatsCards({ scan }: { scan: BackendScanResponse | null }) {
  const listings = scan?.flagged_listings ?? []

  // Only average listings that are actually cheaper than the official price.
  // Listings priced ABOVE official (common noise from mismatched/irrelevant
  // search results) are excluded so the average never goes negative/confusing.
  const belowMsrp = listings.filter(
    (l) => l.listing_price != null && l.listing_price > 0 && l.listing_price < l.official_price,
  )
  const avgDeviation =
    belowMsrp.length > 0
      ? Math.round(
          belowMsrp.reduce(
            (sum, l) => sum + ((l.official_price - (l.listing_price as number)) / l.official_price) * 100,
            0,
          ) / belowMsrp.length,
        )
      : 0

  const stats: Stat[] = [
    {
      label: 'Engines Queried',
      value: scan ? String(scan.engines_used.length) : '—',
      sub: 'live SerpApi engines',
      trend: scan ? (scan.cached ? 'from cache' : 'live scan') : 'not scanned yet',
      trendUp: true,
      icon: Database,
      tone: 'text-primary',
      toneBg: 'bg-primary/10',
    },
    {
      label: 'Flagged Infringements',
      value: scan ? String(listings.length) : '—',
      sub: 'require review',
      trend: scan ? `${scan.new_infringements.length} new` : '—',
      trendUp: true,
      icon: ShieldAlert,
      tone: 'text-[var(--danger)]',
      toneBg: 'bg-[var(--danger)]/10',
    },
    {
      label: 'Avg. Discount Deviation',
      value: scan ? (belowMsrp.length > 0 ? `${avgDeviation}%` : 'N/A') : '—',
      sub: belowMsrp.length > 0 ? 'below official MSRP' : 'no listings priced below MSRP',
      trend: scan ? 'this scan' : '—',
      trendUp: true,
      icon: TrendingDown,
      tone: 'text-[var(--warning)]',
      toneBg: 'bg-[var(--warning)]/10',
    },
    {
      label: 'Overall Threat Level',
      value: scan ? threatLabel(scan.risk_score) : '—',
      sub: 'weighted risk index',
      trend: scan ? 'action advised' : 'run a scan',
      trendUp: false,
      icon: AlertTriangle,
      tone: 'text-orange-400',
      toneBg: 'bg-orange-400/10',
    },
  ]

  return (
    <section aria-label="Key metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map((s) => {
        const Icon = s.icon
        return (
          <div
            key={s.label}
            className="rounded-xl border border-border bg-card p-4 transition hover:border-border/70 hover:bg-card/80"
          >
            <div className="flex items-start justify-between">
              <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${s.toneBg}`}>
                <Icon className={`h-4.5 w-4.5 ${s.tone}`} aria-hidden="true" />
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                  s.trendUp ? 'bg-secondary text-muted-foreground' : 'bg-orange-400/10 text-orange-400'
                }`}
              >
                {s.trend}
              </span>
            </div>
            <p className="mt-4 text-2xl font-semibold tracking-tight tabular-nums">
              {s.value}
            </p>
            <p className="mt-1 text-sm font-medium">{s.label}</p>
            <p className="text-xs text-muted-foreground">{s.sub}</p>
          </div>
        )
      })}
    </section>
  )
}
