import { NextRequest } from 'next/server'
import { servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'

// FINRA Reg SHO gunluk kisa-hacim orani — /api/finra-darkpool ile AYNI
// servise (finra-darkpool-service) gider, farkli bir ucuna (/regsho).
// Koyfin olay katmani icin GUNLUK granulerlikte veri gerekiyordu;
// /darkpool ucu yalnizca haftalik ozet veriyor (bkz.
// frontend/HATA_HAFIZASI_koyfin.md H-001). Yeni bir DIS servis/anahtar
// DEGIL — mevcut ucretsiz, anahtarsiz servisin ikinci bir ucu
// (frontend/VARSAYIM_DEFTERI_koyfin.md V-007, coz).
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  return servisProxy({
    taban: process.env.FINRA_DARKPOOL_URL || 'http://alphawise-finra-darkpool:8000',
    yol: `/regsho/${encodeURIComponent(t)}`,
    zamanAsimiMs: 60_000,
    servisAdi: 'FINRA Reg SHO',
  })
}
