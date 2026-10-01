'use client'

import { useMemo, useState } from 'react'
import { CeaseDesistModal } from '@/components/cease-desist-modal'
import { InfringementsTable } from '@/components/infringements-table'
import { Navbar } from '@/components/navbar'
import { RiskGauge } from '@/components/risk-gauge'
import { SearchSection } from '@/components/search-section'
import { StatsCards } from '@/components/stats-cards'
import { mapListingToInfringement, type BackendScanResponse } from '@/lib/api'
import type { Infringement } from '@/lib/data'

export default function Page() {
  const [scan, setScan] = useState<BackendScanResponse | null>(null)
  const [selected, setSelected] = useState<Infringement | null>(null)
  const [open, setOpen] = useState(false)

  const infringements: Infringement[] = useMemo(
    () => (scan ? scan.flagged_listings.map(mapListingToInfringement) : []),
    [scan],
  )

  const handleAction = (item: Infringement) => {
    setSelected(item)
    setOpen(true)
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto max-w-[1400px] space-y-5 px-4 py-6 sm:px-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            IP Protection Dashboard
          </h1>
          <p className="text-sm text-muted-foreground">
            Real-time counterfeit detection and brand-abuse threat intelligence.
          </p>
        </div>

        <SearchSection onScanComplete={setScan} />
        <StatsCards scan={scan} />

        <div className="grid gap-5 lg:grid-cols-[minmax(280px,340px)_1fr]">
          <RiskGauge score={scan?.risk_score ?? 0} listings={infringements} />
          <InfringementsTable
            items={infringements}
            hasScanned={!!scan}
            currency={scan?.currency ?? 'USD'}
            onAction={handleAction}
          />
        </div>
      </main>

      <CeaseDesistModal
        item={selected}
        open={open}
        onClose={() => setOpen(false)}
        legalNoticeBody={scan?.legal_notice_draft?.body}
        currency={scan?.currency ?? 'USD'}
      />
    </div>
  )
}
