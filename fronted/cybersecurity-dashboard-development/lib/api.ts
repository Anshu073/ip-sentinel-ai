export type Currency = 'USD' | 'INR'

export const CURRENCY_SYMBOL: Record<Currency, string> = {
  USD: '$',
  INR: '₹',
}

export type BackendFactorBreakdown = {
  weight: number
  score: number
  triggered: boolean
  detail: string
}

export type BackendFlaggedListing = {
  id: string
  title?: string | null
  source_engine: string
  seller_name?: string | null
  seller_rating?: number | null
  listing_price?: number | null
  official_price: number
  risk_score: number
  domain?: string | null
  domain_created_at?: string | null
  evidence: {
    matched_image?: string | null
    listing_url: string
    price?: number | null
    timestamp: string
    whois_domain_age?: string | null
  }
  factor_scores: Record<string, any>
}

export type BackendScanResponse = {
  scan_id: string
  product_name: string
  official_price: number
  image_url: string
  scanned_at: string
  cached: boolean
  currency: Currency
  watch_id?: string | null
  rescan_interval_hours?: number | null
  risk_score: number
  risk_breakdown: {
    price_deviation: BackendFactorBreakdown
    seller_credibility: BackendFactorBreakdown
    visual_brand_match: BackendFactorBreakdown
    domain_risk: BackendFactorBreakdown
  }
  flagged_listings: BackendFlaggedListing[]
  new_infringements: BackendFlaggedListing[]
  engines_used: string[]
  legal_notice_draft: {
    subject: string
    body: string
    listings_cited: number
    disclaimer: string
  }
  warnings: string[]
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'

export async function runScan(input: {
  product_name: string
  official_price: number
  image_url: string
  currency: Currency
}): Promise<BackendScanResponse> {
  const res = await fetch(`${API_BASE}/api/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })

  if (!res.ok) {
    let message = `Scan failed (HTTP ${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) {
        message = Array.isArray(body.detail)
          ? body.detail.map((d: any) => d.msg).join(', ')
          : String(body.detail)
      }
    } catch {
      // ignore parse errors, keep default message
    }
    throw new Error(message)
  }

  return res.json()
}

function friendlyPlatform(sourceEngine: string) {
  const map: Record<string, string> = {
    google_shopping: 'Google Shopping',
    google_reverse_image: 'Reverse Image Match',
    google: 'Web Search',
  }
  return map[sourceEngine] ?? sourceEngine
}

export function mapListingToInfringement(listing: BackendFlaggedListing) {
  // The backend sends each factor's points as a number (price_deviation: 40)
  // plus a matching text explanation (price_detail: "Listing price ...").
  const fs = listing.factor_scores ?? {}
  const factors = [
    { key: 'price_deviation', detail: 'price_detail', label: 'Price', max: 40 },
    { key: 'seller_credibility', detail: 'seller_detail', label: 'Seller', max: 20 },
    { key: 'visual_brand_match', detail: 'visual_detail', label: 'Visual', max: 20 },
    { key: 'domain_risk', detail: 'domain_detail', label: 'Domain', max: 20 },
  ]

  const signals: string[] = factors
    .filter((f) => Number(fs[f.key]) > 0)
    .map((f) => `${f.label} +${Number(fs[f.key]).toFixed(1)} / ${f.max} — ${fs[f.detail] ?? ''}`)

  if (signals.length === 0) {
    signals.push('No individual factor scored points for this listing.')
  }

  const visualPts = Number(fs.visual_brand_match) || 0
  const imageMatch = Math.round((visualPts / 20) * 100)

  return {
    id: listing.id,
    platform: friendlyPlatform(listing.source_engine),
    seller: listing.seller_name || listing.domain || 'Unknown seller',
    sellerRating:
      listing.seller_rating != null ? Math.round((listing.seller_rating / 5) * 100) : 0,
    listingPrice: listing.listing_price ?? 0,
    officialPrice: listing.official_price,
    fraudScore: Math.round(listing.risk_score),
    listingUrl: listing.evidence.listing_url,
    productTitle: listing.title || 'Untitled listing',
    evidence: {
      firstSeen: listing.evidence.timestamp?.slice(0, 10) || 'Unknown',
      location: listing.domain || 'Unknown',
      signals,
      imageMatch,
      notes: listing.evidence.whois_domain_age
        ? `Domain age: ${listing.evidence.whois_domain_age}`
        : 'No additional domain notes available.',
    },
  }
}
