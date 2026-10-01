'use client'

import { useState } from 'react'
import { AlertCircle, Link2, Loader2, Radar, Tag } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { runScan, type BackendScanResponse, type Currency } from '@/lib/api'

export function SearchSection({
  onScanComplete,
}: {
  onScanComplete: (result: BackendScanResponse) => void
}) {
  const [productName, setProductName] = useState('')
  const [price, setPrice] = useState('')
  const [currency, setCurrency] = useState<Currency>('USD')
  const [imageUrlInput, setImageUrlInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastScanAt, setLastScanAt] = useState<string | null>(null)

  const handleScan = async () => {
    setError(null)

    const priceNum = Number.parseFloat(price)
    if (!productName.trim()) {
      setError('Enter a product name.')
      return
    }
    if (!priceNum || priceNum <= 0) {
      setError('Enter a valid official price.')
      return
    }
    if (!imageUrlInput.trim()) {
      setError('Paste a public URL for the official product image (e.g. the image link from the brand\'s own product page).')
      return
    }

    setLoading(true)
    try {
      const result = await runScan({
        product_name: productName.trim(),
        official_price: priceNum,
        image_url: imageUrlInput.trim(),
        currency,
      })
      onScanComplete(result)
      setLastScanAt(new Date().toLocaleTimeString())
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not reach the backend. Is it running on localhost:8000?',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section
      aria-label="Product monitoring configuration"
      className="rounded-xl border border-border bg-card p-4 sm:p-5"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Radar className="h-4 w-4 text-primary" aria-hidden="true" />
          <h2 className="text-sm font-semibold">New Protection Scan</h2>
        </div>
        <span className="hidden text-xs text-muted-foreground sm:inline">
          Define the genuine product to detect infringing listings
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1.1fr]">
        <div className="space-y-1.5">
          <label htmlFor="product-name" className="text-xs font-medium text-muted-foreground">
            Product Name
          </label>
          <div className="relative">
            <Tag
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              id="product-name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="e.g. Apple AirPods Pro 2nd Generation"
              className="h-11 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm outline-none ring-primary/40 transition placeholder:text-muted-foreground/60 focus:border-primary/60 focus:ring-2"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="official-price" className="text-xs font-medium text-muted-foreground">
            Official Price
          </label>
          <div className="flex gap-2">
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value as Currency)}
              aria-label="Currency"
              className="h-11 shrink-0 rounded-lg border border-input bg-background px-2 text-sm outline-none ring-primary/40 transition focus:border-primary/60 focus:ring-2"
            >
              <option value="USD">USD ($)</option>
              <option value="INR">INR (₹)</option>
            </select>
            <div className="relative flex-1">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm text-muted-foreground">
                {currency === 'INR' ? '₹' : '$'}
              </span>
              <input
                id="official-price"
                inputMode="decimal"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="0.00"
                className="h-11 w-full rounded-lg border border-input bg-background pl-8 pr-3 font-mono text-sm outline-none ring-primary/40 transition placeholder:text-muted-foreground/60 focus:border-primary/60 focus:ring-2"
              />
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground">
            {currency === 'INR'
              ? 'Search runs on Google India (gl=in) — results and prices are in INR.'
              : 'Search runs on Google US (gl=us) — results and prices are in USD.'}
          </p>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="image-url" className="text-xs font-medium text-muted-foreground">
            Official Product Image URL
          </label>
          <div className="relative">
            <Link2
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              id="image-url"
              value={imageUrlInput}
              onChange={(e) => setImageUrlInput(e.target.value)}
              placeholder="https://brand-site.com/product-photo.jpg"
              className="h-11 w-full rounded-lg border border-input bg-background pl-9 pr-3 text-sm outline-none ring-primary/40 transition placeholder:text-muted-foreground/60 focus:border-primary/60 focus:ring-2"
            />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Must be a public link (e.g. from the brand&apos;s own product page).
          </p>
        </div>
      </div>

      {error && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-xs text-[var(--danger)]">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <p className="text-xs text-muted-foreground">
          {lastScanAt ? (
            <>
              Last scan completed <span className="text-foreground">{lastScanAt}</span>
            </>
          ) : (
            'No scans run yet this session'
          )}
        </p>
        <Button className="gap-2" onClick={handleScan} disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Scanning SerpApi…
            </>
          ) : (
            <>
              <Radar className="h-4 w-4" aria-hidden="true" />
              Run Deep Scan
            </>
          )}
        </Button>
      </div>
    </section>
  )
}
