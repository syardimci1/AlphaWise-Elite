import { NextRequest } from 'next/server'
import { servisProxy } from '@/lib/servis-proxy'

// FRED Makro Servisi (8270) — makro yayin takvimi + gostergeler.
//
// TICKER ALMAZ: bu sinyal hisseye bagli degildir, tum piyasa icin
// ayni. Ayni desen /api/liquidity-signal'de de kullanildi.
//
// LIQUIDITY-SIGNAL ILE KARISTIRILMAMALI: o servis Fed bilanco/likidite
// serilerini (WALCL/TGA/RRP/M2) okur ve kalibrasyonu basarisiz oldugu
// icin lambda=0'da durur. Bu servis takvim + getiri egrisi/cekirdek
// PCE/istihdam/basvuru/guven/dolar okur; seri kesisimi SIFIRDIR.
//
// ZAMAN ASIMI: soguk cagride 6 FRED serisi + takvim cekiliyor; sicak
// cagri Redis onbelleginden (gosterge 6 sa, takvim 12 sa) donuyor.
export async function GET(_req: NextRequest) {
  return servisProxy({
    taban: process.env.FRED_MACRO_URL || 'http://alphawise-fred-macro:8000',
    yol: '/ozet',
    zamanAsimiMs: 90_000,
    servisAdi: 'FRED Makro Takvimi',
  })
}
