import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// Finnhub Sinyal Servisi (8280) — sirket takvimi + haber yogunlugu.
//
// KOTA NOTU: Finnhub ucretsiz katman limiti CANLI OLCULDU, anahtar
// basina dakikada 60 istek (x-ratelimit-limit basligi). Ayni anahtar
// havuzunu saa ve news-monitor de kullaniyor; news-monitor 7/24 sabit
// yuk uretiyor. Bu yuzden servis kendi payini Redis sayaciyla
// sinirliyor ve pay dolarsa AG CAGRISI YAPMADAN 429 donuyor — o durumda
// bu proxy 429'u oldugu gibi kullaniciya tasir.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.FINNHUB_SIGNAL_URL || 'http://alphawise-finnhub-signal:8000',
    yol: `/sirket/${encodeURIComponent(t)}`,
    zamanAsimiMs: 60_000,
    servisAdi: 'Sirket Takvimi ve Haber Yogunlugu',
  })
}
