'use client'

import { Fragment, useState } from 'react'
import {
  ChevronDown,
  ExternalLink,
  FileText,
  Fingerprint,
  MapPin,
  Radar,
  Star,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CURRENCY_SYMBOL, type Currency } from '@/lib/api'
import type { Infringement } from '@/lib/data'

function fraudTone(score: number) {
  if (score >= 80) return 'text-[var(--danger)] bg-[var(--danger)]/10 ring-[var(--danger)]/30'
  if (score >= 60) return 'text-orange-400 bg-orange-400/10 ring-orange-400/30'
  if (score >= 35) return 'text-[var(--warning)] bg-[var(--warning)]/10 ring-[var(--warning)]/30'
  return 'text-[var(--success)] bg-[var(--success)]/10 ring-[var(--success)]/30'
}

// Returns a human sentence for the price comparison. Listings priced ABOVE
// the official price are labelled "above official price" instead of a
// confusing negative "% below MSRP".
function priceDeviationLabel(listingPrice: number, officialPrice: number) {
  if (!officialPrice || listingPrice <= 0) return 'Price unavailable'
  if (listingPrice >= officialPrice) {
    const pctAbove = Math.round(((listingPrice - officialPrice) / officialPrice) * 100)
    return `${pctAbove}% above official price`
  }
  const pctBelow = Math.round(((officialPrice - listingPrice) / officialPrice) * 100)
  return `${pctBelow}% below MSRP`
}

export function InfringementsTable({
  items,
  hasScanned,
  currency = 'USD',
  onAction,
}: {
  items: Infringement[]
  hasScanned: boolean
  currency?: Currency
  onAction: (item: Infringement) => void
}) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const symbol = CURRENCY_SYMBOL[currency]

  return (
    <section
      aria-label="Detected infringements"
      className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card"
    >
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold">Detected Infringements</h2>
          <p className="text-xs text-muted-foreground">
            {items.length} listings flagged against official product
          </p>
        </div>
        <span className="rounded-full bg-[var(--danger)]/10 px-2.5 py-1 text-xs font-medium text-[var(--danger)] ring-1 ring-[var(--danger)]/30">
          Live monitoring
        </span>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-5 py-16 text-center">
          <Radar className="h-8 w-8 text-muted-foreground/50" aria-hidden="true" />
          <p className="text-sm font-medium text-foreground">
            {hasScanned ? 'No infringements found on this scan' : 'No scan run yet'}
          </p>
          <p className="max-w-sm text-xs text-muted-foreground">
            {hasScanned
              ? 'SerpApi did not return any listings matching the fraud criteria for this product.'
              : 'Fill in the form above and click "Run Deep Scan" to query live SerpApi data.'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-5 py-3 font-medium">Platform / Seller</th>
                <th className="px-3 py-3 font-medium">Listing vs Official</th>
                <th className="px-3 py-3 font-medium">Fraud Score</th>
                <th className="px-3 py-3 text-right font-medium">Action</th>
                <th className="w-10 px-3 py-3" />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const isOpen = expanded === item.id
                const deviationLabel = priceDeviationLabel(item.listingPrice, item.officialPrice)
                const isAboveOfficial = item.listingPrice >= item.officialPrice
                return (
                  <Fragment key={item.id}>
                    <tr
                      className={`border-b border-border/60 align-top transition-colors ${
                        isOpen ? 'bg-secondary/40' : 'hover:bg-secondary/25'
                      }`}
                    >
                      <td className="px-5 py-4">
                        <p className="font-medium">{item.platform}</p>
                        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                          <span>{item.seller}</span>
                          <span className="inline-flex items-center gap-0.5">
                            <Star
                              className="h-3 w-3 fill-[var(--warning)] text-[var(--warning)]"
                              aria-hidden="true"
                            />
                            {item.sellerRating}%
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-4">
                        <div className="flex items-baseline gap-2">
                          <span
                            className={`font-mono font-semibold ${
                              isAboveOfficial ? 'text-foreground' : 'text-[var(--danger)]'
                            }`}
                          >
                            {symbol}
                            {item.listingPrice.toFixed(2)}
                          </span>
                          <span className="font-mono text-xs text-muted-foreground line-through">
                            {symbol}
                            {item.officialPrice.toFixed(2)}
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-muted-foreground">{deviationLabel}</p>
                      </td>
                      <td className="px-3 py-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded-md px-2 py-1 font-mono text-xs font-semibold ring-1 ${fraudTone(item.fraudScore)}`}
                          >
                            {item.fraudScore}%
                          </span>
                          <div className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-secondary sm:block">
                            <div
                              className="h-full rounded-full bg-current"
                              style={{
                                width: `${item.fraudScore}%`,
                                color:
                                  item.fraudScore >= 80
                                    ? 'var(--danger)'
                                    : item.fraudScore >= 60
                                      ? 'oklch(0.7 0.18 45)'
                                      : 'var(--warning)',
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-4 text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          className="gap-1.5 border-[var(--danger)]/40 text-[var(--danger)] hover:bg-[var(--danger)]/10 hover:text-[var(--danger)]"
                          onClick={() => onAction(item)}
                        >
                          <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                          Take Down
                        </Button>
                      </td>
                      <td className="px-3 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => setExpanded(isOpen ? null : item.id)}
                          aria-expanded={isOpen}
                          aria-label={`${isOpen ? 'Hide' : 'Show'} evidence for ${item.id}`}
                          className="rounded-md p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                        >
                          <ChevronDown
                            className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                            aria-hidden="true"
                          />
                        </button>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-background/40">
                        <td colSpan={5} className="px-5 pb-5 pt-1">
                          <div className="rounded-lg border border-border bg-popover p-4">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div className="flex items-center gap-2">
                                <Fingerprint className="h-4 w-4 text-primary" aria-hidden="true" />
                                <span className="text-xs font-semibold">
                                  Evidence · {item.id}
                                </span>
                              </div>
                              <a
                                href={
                                  item.listingUrl.startsWith('http')
                                    ? item.listingUrl
                                    : `https://${item.listingUrl}`
                                }
                                target="_blank"
                                rel="noreferrer noopener"
                                className="inline-flex items-center gap-1 truncate font-mono text-xs text-primary hover:underline"
                              >
                                <span className="max-w-[280px] truncate sm:max-w-[420px]">
                                  {item.listingUrl}
                                </span>
                                <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
                              </a>
                            </div>

                            <p className="mt-3 text-sm text-foreground">{item.productTitle}</p>

                            <div className="mt-4 grid gap-4 md:grid-cols-[1fr_180px]">
                              <div>
                                <p className="mb-2 text-xs font-medium text-muted-foreground">
                                  Detection signals
                                </p>
                                <ul className="space-y-1.5">
                                  {item.evidence.signals.map((sig) => (
                                    <li
                                      key={sig}
                                      className="flex items-start gap-2 text-xs text-foreground/90"
                                    >
                                      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--danger)]" />
                                      {sig}
                                    </li>
                                  ))}
                                </ul>
                                <p className="mt-3 rounded-md bg-secondary/60 p-2.5 text-xs text-muted-foreground">
                                  {item.evidence.notes}
                                </p>
                              </div>
                              <div className="space-y-3 rounded-md bg-secondary/40 p-3">
                                <div>
                                  <p className="text-[11px] text-muted-foreground">Visual match</p>
                                  <p className="font-mono text-lg font-semibold text-primary">
                                    {item.evidence.imageMatch}%
                                  </p>
                                </div>
                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                  <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                                  {item.evidence.location}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  First seen{' '}
                                  <span className="text-foreground">{item.evidence.firstSeen}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
