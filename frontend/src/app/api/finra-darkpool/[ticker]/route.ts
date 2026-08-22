import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// FINRA Dark Pool — FINRA'nin resmi ATS Transparency haftalik hacim verisi.
// Anahtar gerektirmez, ucretsizdir. Veri HAFTALIK yayimlanir ve gecmise
// donuktur; anlik piyasa gorunumu degildir.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.FINRA_DARKPOOL_URL || 'http://alphawise-finra-darkpool:8000',
    yol: `/darkpool/${encodeURIComponent(t)}`,
    zamanAsimiMs: 60_000,
    servisAdi: 'FINRA Dark Pool',
  })
}
