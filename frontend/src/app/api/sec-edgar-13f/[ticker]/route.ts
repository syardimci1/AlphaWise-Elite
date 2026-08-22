import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// SEC EDGAR 13F — kurumsal pozisyonlar, SEC'in resmi acik verisinden.
// API anahtari gerektirmez, ucretsizdir. Adres yalnizca sunucuda tutulur.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.SEC_EDGAR_13F_URL || 'http://alphawise-sec-edgar-13f:8000',
    // Servis kendi icinde SEC'in 10 istek/sn sinirina uymak icin bekliyor;
    // birden cok kurum tarandigi icin zaman asimi genis tutuldu.
    yol: `/holders/${encodeURIComponent(t)}?top=8`,
    zamanAsimiMs: 120_000,
    servisAdi: 'SEC EDGAR 13F',
  })
}
