import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// SEC Form 4 — sirket ici yonetici islemleri. SEC'in resmi acik verisi,
// ucretsiz ve anahtarsiz. Adres yalnizca sunucuda tutulur.
//
// ONEMLI: Bu servis YON KODU URETMEZ (lambda = 0). Deney 1 olctu: 25
// mega-cap x 3,57 yilda yalnizca 32 acik piyasa alimi var (29'u tek
// hissede) — yon kalibrasyonu bu evrende matematiksel olarak mumkun degil.
// Kisit servis tarafinda kod seviyesinde uygulanir (lambda_sifir.py).
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.INSIDER_TRADING_URL || 'http://alphawise-insider-trading:8000',
    // Soguk istek olculdu: 26,3 sn (SEC'ten cekim). Servis ticker basina
    // 6 saat onbellek tutuyor, sicak istek ~1,2 sn.
    yol: `/insider/${encodeURIComponent(t)}/ozet`,
    zamanAsimiMs: 90_000,
    servisAdi: 'SEC Form 4 (iceriden islem)',
  })
}
