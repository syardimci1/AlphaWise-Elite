import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// Gamma Exposure servisi — iki ayri gostergesi var:
//   /gex/{ticker}      : FlashAlpha opsiyon GEX verisi
//   /dix-like/{ticker} : FINRA dark pool verisinden hesaplanan DPKE
//                        (Dark Pool Katilim Endeksi) — resmi DIX DEGILDIR
//
// NEDEN VARSAYILAN OLARAK /gex CAGIRILMIYOR (OLCUME DAYALI KARAR, 22.08.2026):
// Ucretsiz FlashAlpha tier'inde /gex her cagride HTTP 402 donuyor
// ("plan/tier kisitlamasi" — anahtar sorunu degil, tum ucretsiz anahtarlar
// ayni kisita tabi). ANCAK basarisiz cagri bile gunluk kotadan dusuyor:
// tek denemede kota 25'ten 24'e indi. Dashboard her hisse sorgusunda /gex'i
// otomatik cagirsaydi, hicbir veri alamadan gunluk 25 kotanin tamami
// tukenirdi. Bu yuzden bu route DPKE'yi dondurur; GEX'in ucretsiz planda
// kapali oldugu arayuzde ACIKCA yazilir.
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.GAMMA_EXPOSURE_URL || 'http://alphawise-gamma-exposure:8000',
    yol: `/dix-like/${encodeURIComponent(t)}`,
    zamanAsimiMs: 60_000,
    servisAdi: 'Dark Pool Katilim Endeksi',
  })
}
