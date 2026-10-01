'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, Check, Copy, ScrollText, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CURRENCY_SYMBOL, type Currency } from '@/lib/api'
import type { Infringement } from '@/lib/data'

function buildLocalNotice(item: Infringement, symbol: string) {
  const today = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
  const priceLine =
    item.listingPrice >= item.officialPrice
      ? `priced ${symbol}${item.listingPrice.toFixed(2)}, above the Company's official price of ${symbol}${item.officialPrice.toFixed(2)}`
      : `a ${Math.round(((item.officialPrice - item.listingPrice) / item.officialPrice) * 100)}% deviation below the Company's official price of ${symbol}${item.officialPrice.toFixed(2)}`

  return `CEASE & DESIST NOTICE (DRAFT — NOT LEGAL ADVICE)
Ref: ${item.id} · Generated ${today}

TO: ${item.seller} (via ${item.platform})
LISTING: ${item.listingUrl}

RE: Unauthorized Use of Intellectual Property and Sale of Infringing Goods

Dear Seller,

We are writing on behalf of the rights holder (the "Company") concerning the listing identified above offering "${item.productTitle}". Our automated monitoring has identified this listing with a fraud-risk score of ${item.fraudScore}% and ${priceLine}.

DEMANDS
You are hereby demanded to, within seventy-two (72) hours of receipt of this notice:
  (a) Immediately and permanently remove the infringing listing(s);
  (b) Cease all manufacture, marketing, distribution, and sale of the infringing goods;
  (c) Cease all use of the Company's copyrighted images and trademarks.

This is an AI-generated draft template for brand/legal team review — not legal advice.

Sincerely,
IP Enforcement Team
On behalf of the Rights Holder`
}

export function CeaseDesistModal({
  item,
  open,
  onClose,
  legalNoticeBody,
  currency = 'USD',
}: {
  item: Infringement | null
  open: boolean
  onClose: () => void
  legalNoticeBody?: string
  currency?: Currency
}) {
  const [copied, setCopied] = useState(false)
  const symbol = CURRENCY_SYMBOL[currency]

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  useEffect(() => {
    setCopied(false)
  }, [item])

  const notice = item ? legalNoticeBody || buildLocalNotice(item, symbol) : ''

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(notice)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div
      className={`fixed inset-0 z-50 ${open ? '' : 'pointer-events-none'}`}
      aria-hidden={!open}
    >
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300 ${
          open ? 'opacity-100' : 'opacity-0'
        }`}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Cease and desist legal notice"
        className={`absolute right-0 top-0 flex h-full w-full max-w-xl flex-col border-l border-border bg-card shadow-2xl transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/30">
              <ScrollText className="h-4.5 w-4.5 text-primary" aria-hidden="true" />
            </span>
            <div>
              <h2 className="text-sm font-semibold">Cease &amp; Desist Notice</h2>
              <p className="text-xs text-muted-foreground">
                Auto-generated{item ? ` · ${item.id} · ${item.platform}` : ''}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="flex items-start gap-2.5 border-b border-[var(--warning)]/30 bg-[var(--warning)]/10 px-5 py-3">
          <AlertTriangle
            className="mt-0.5 h-4 w-4 shrink-0 text-[var(--warning)]"
            aria-hidden="true"
          />
          <p className="text-xs text-[var(--warning)]">
            <span className="font-semibold">Not legal advice.</span> This document is a
            machine-generated draft template. Review by qualified legal counsel is required
            before sending or relying on it.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground/90">
            {notice}
          </pre>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border px-5 py-4">
          <p className="text-xs text-muted-foreground">
            Draft generated by IP-Sentinel AI
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button className="gap-2" onClick={copy}>
              {copied ? (
                <>
                  <Check className="h-4 w-4" aria-hidden="true" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" aria-hidden="true" />
                  Copy Notice
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
