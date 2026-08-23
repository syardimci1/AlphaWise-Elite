import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// DEX / GEX / Vanna — opsiyon maruziyeti (gamma-exposure-service /dex-vanna).
//
// NEDEN AYRI BIR UC (ayni servisteki /gex ile karistirilmamali):
// /gex ucretsiz FlashAlpha planinda HTTP 402 donuyor ve BASARISIZ cagri bile
// gunluk 25'lik kotadan dusuyor. /dex-vanna ise zinciri openbb-service
// uzerinden yfinance'ten aliyor: ucretsiz, anahtarsiz ve FlashAlpha kotasina
// HIC dokunmuyor (olculdu: hesap sonrasi /quota 0/25, degismedi).
//
// ZAMAN ASIMI: soguk hesap olculdu (AAPL, 2.418 kontrat) ~20-40 sn; sicak
// (Redis, TTL 900 sn) <1 sn. 120 sn genis bir pay birakir.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.GAMMA_EXPOSURE_URL || 'http://alphawise-gamma-exposure:8000',
    yol: `/dex-vanna/${encodeURIComponent(t)}`,
    zamanAsimiMs: 120_000,
    servisAdi: 'Opsiyon Maruziyeti (DEX/GEX/Vanna)',
  })
}
