export type ThreatLevel = 'low' | 'moderate' | 'elevated' | 'critical'

export type Infringement = {
  id: string
  platform: string
  seller: string
  sellerRating: number
  listingPrice: number
  officialPrice: number
  fraudScore: number
  listingUrl: string
  productTitle: string
  evidence: {
    firstSeen: string
    location: string
    signals: string[]
    imageMatch: number
    notes: string
  }
}

export const OFFICIAL_PRICE = 199.0

export const infringements: Infringement[] = [
  {
    id: 'INF-4821',
    platform: 'AliExpress',
    seller: 'GlobalGadgetHub',
    sellerRating: 78,
    listingPrice: 42.99,
    officialPrice: OFFICIAL_PRICE,
    fraudScore: 96,
    listingUrl: 'aliexpress.com/item/1005-4821',
    productTitle: 'Wireless Noise-Cancelling Headphones PRO (OEM)',
    evidence: {
      firstSeen: '2026-09-02',
      location: 'Shenzhen, CN',
      signals: [
        'Uses official product photography without license',
        'Price 78% below MSRP',
        'Trademarked logo present on listing images',
        'Bulk quantity available (>10,000 units)',
      ],
      imageMatch: 98,
      notes:
        'Listing reuses three copyrighted marketing renders. Serial number format does not match manufacturer schema.',
    },
  },
  {
    id: 'INF-4790',
    platform: 'Amazon Marketplace',
    seller: 'PrimeDealsDirect',
    sellerRating: 64,
    listingPrice: 89.5,
    officialPrice: OFFICIAL_PRICE,
    fraudScore: 88,
    listingUrl: 'amazon.com/dp/B0C-4790',
    productTitle: 'NC Headphones PRO — Factory Sealed',
    evidence: {
      firstSeen: '2026-09-08',
      location: 'Newark, US',
      signals: [
        'Counterfeit packaging detected in customer photos',
        'Price 55% below MSRP',
        'Seller registered < 30 days ago',
      ],
      imageMatch: 84,
      notes:
        'Multiple buyer reviews report missing warranty card and mismatched firmware. Grey-market import suspected.',
    },
  },
  {
    id: 'INF-4763',
    platform: 'eBay',
    seller: 'audio_liquidators',
    sellerRating: 71,
    listingPrice: 74.0,
    officialPrice: OFFICIAL_PRICE,
    fraudScore: 82,
    listingUrl: 'ebay.com/itm/4763',
    productTitle: 'Headphones PRO — New Other (See Details)',
    evidence: {
      firstSeen: '2026-09-11',
      location: 'Guangzhou, CN',
      signals: [
        'Image hash matches known counterfeit cluster',
        'Price 63% below MSRP',
        'Stock photos with edited watermark',
      ],
      imageMatch: 91,
      notes:
        'Watermark removal artifacts detected on 4 of 6 listing images. Cross-listed under 2 other seller aliases.',
    },
  },
  {
    id: 'INF-4740',
    platform: 'Walmart Marketplace',
    seller: 'ElectroValueLLC',
    sellerRating: 83,
    listingPrice: 129.99,
    officialPrice: OFFICIAL_PRICE,
    fraudScore: 61,
    listingUrl: 'walmart.com/ip/4740',
    productTitle: 'Wireless Headphones PRO (Open Box)',
    evidence: {
      firstSeen: '2026-09-14',
      location: 'Austin, US',
      signals: [
        'Price 35% below MAP agreement',
        'Unauthorized reseller — not in distributor list',
      ],
      imageMatch: 62,
      notes:
        'Likely MAP violation rather than counterfeit. Product appears genuine but sold outside authorized channel.',
    },
  },
  {
    id: 'INF-4712',
    platform: 'Shopify (Standalone)',
    seller: 'best-audio-outlet.store',
    sellerRating: 41,
    listingPrice: 38.0,
    officialPrice: OFFICIAL_PRICE,
    fraudScore: 94,
    listingUrl: 'best-audio-outlet.store/pro',
    productTitle: 'PRO Headphones — Flash Sale 80% OFF',
    evidence: {
      firstSeen: '2026-09-18',
      location: 'Unknown (Cloudflare proxy)',
      signals: [
        'Clone storefront mimicking official brand site',
        'Price 81% below MSRP',
        'Payment page collects card data on unverified gateway',
        'Domain registered 12 days ago',
      ],
      imageMatch: 99,
      notes:
        'Full brand-impersonation storefront. High phishing risk — replicates official checkout and brand assets pixel-for-pixel.',
    },
  },
]

export function threatFromScore(score: number): ThreatLevel {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'elevated'
  if (score >= 35) return 'moderate'
  return 'low'
}

export const threatMeta: Record<
  ThreatLevel,
  { label: string; text: string; bg: string; ring: string; dot: string }
> = {
  low: {
    label: 'Low',
    text: 'text-[var(--success)]',
    bg: 'bg-[var(--success)]/10',
    ring: 'ring-[var(--success)]/30',
    dot: 'bg-[var(--success)]',
  },
  moderate: {
    label: 'Moderate',
    text: 'text-[var(--warning)]',
    bg: 'bg-[var(--warning)]/10',
    ring: 'ring-[var(--warning)]/30',
    dot: 'bg-[var(--warning)]',
  },
  elevated: {
    label: 'Elevated',
    text: 'text-orange-400',
    bg: 'bg-orange-400/10',
    ring: 'ring-orange-400/30',
    dot: 'bg-orange-400',
  },
  critical: {
    label: 'Critical',
    text: 'text-[var(--danger)]',
    bg: 'bg-[var(--danger)]/10',
    ring: 'ring-[var(--danger)]/30',
    dot: 'bg-[var(--danger)]',
  },
}
