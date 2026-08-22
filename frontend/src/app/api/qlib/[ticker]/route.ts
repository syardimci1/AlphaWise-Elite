import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// Qlib — LightGBM/Alpha158 modelinin urettigi gunluk skor.
//
// Endpoint canli hesaplama YAPMAZ; haftalik yeniden egitimin urettigi
// gunluk skor onbellegini okur (bu yuzden hizlidir). Yanittaki as_of_date
// alani skorun hangi gune ait oldugunu soyler ve dashboard'da gosterilir —
// boylece bayat bir skor "guncel" saniilmaz.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.QLIB_URL || 'http://alphawise-qlib:8000',
    yol: `/predict/${encodeURIComponent(t)}`,
    zamanAsimiMs: 30_000,
    servisAdi: 'Qlib model skoru',
  })
}
