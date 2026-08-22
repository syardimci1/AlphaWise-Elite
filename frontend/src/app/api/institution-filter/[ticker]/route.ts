import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// Institution Filter — LLMQuant uzerinden 13F kurumsal sahiplik.
//
// DURUM NOTU (22.08.2026 canli olcum): LLMQUANT_API_KEY_1 gecerli ama
// kalan kredisi 0; KEY_2 gecersiz (HTTP 401). Sonuc: yalnizca daha once
// sorgulanip Redis'e dusmus hisseler yanit veriyor (ornegin AAPL 200),
// yeni bir hisse sorulunca servis HTTP 502 donuyor (ZBRA ile dogrulandi).
// Bu durum dashboard'da GIZLENMEZ; kullaniciya kredinin bittigi ve bazi
// sorgularin bu yuzden bos donecegi acikca soylenir.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban:
      process.env.INSTITUTION_FILTER_URL ||
      'http://alphawise-institution-filter:8000',
    yol: `/holders/${encodeURIComponent(t)}?top=8`,
    zamanAsimiMs: 60_000,
    servisAdi: 'Institution Filter (LLMQuant)',
  })
}
