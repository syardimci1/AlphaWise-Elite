import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// Congress Trading — ABD Kongre uyelerinin STOCK Act kapsaminda acikladigi
// hisse islemleri.
//
// DURUM NOTU (22.08.2026 canli olcum): Birincil kaynak Quiver HTTP 403
// donuyor ("Upgrade your subscription plan"). Servis otomatik olarak FMP
// yedegine dusuyor ve calisiyor (200 kayit). Yanittaki source/fallback_used
// alanlari dashboard'da gosterilir; hangi kaynaktan geldigi gizlenmez.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban:
      process.env.CONGRESS_TRADING_URL || 'http://alphawise-congress-trading:8000',
    yol: `/trades/${encodeURIComponent(t)}?limit=10`,
    zamanAsimiMs: 90_000,
    servisAdi: 'Congress Trading',
  })
}
