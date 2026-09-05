import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// Bes eksenli temel skor sentezi (Madde 23).
//
// Servis mali tablolari yfinance'tan CANLI cekip Altman Z / Beneish M /
// Piotroski F / DCF hesapladigi icin yanit suresi tek bir ticker'da
// olculdugunde ~20-40 saniye arasinda degisiyor (dort ayri tablo + ^TNX).
// Bu yuzden zaman asimi diger servislerden yuksek tutuldu; daha kisa bir
// deger, veri GELIRKEN kullaniciya "zaman asimi" gostermeye yol acardi.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.SKOR_SENTEZI_URL || 'http://alphawise-skor-sentezi:8000',
    yol: `/skor/${encodeURIComponent(t)}`,
    zamanAsimiMs: 90_000,
    servisAdi: 'Bes eksenli skor sentezi',
  })
}
