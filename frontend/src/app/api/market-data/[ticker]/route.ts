import { NextRequest, NextResponse } from 'next/server'
import { istekKimligi, servisProxy, tickerDogrula, gecersizTicker } from '@/lib/servis-proxy'
import { limitDogrula, limitSorguDizesi } from '@/lib/grafik/veri-penceresi'

// market-data-service icin sunucu-tarafi proxy — DIGER 4 route'la (congress/
// insider/13f/finra) AYNI kalip.
//
// NEDEN EKLENDI (koyfin olay katmani calismasi sirasinda kendi kendine
// bulunan hata, bkz. frontend/HATA_HAFIZASI_koyfin.md H-002):
// PriceChart.tsx GERCEK bir tarayicida canli test edilirken, NEXT_PUBLIC_
// MARKET_DATA_URL uzerinden DOGRUDAN market-data-service'e (127.0.0.1:8160)
// tarayicidan fetch attigi ve o servis CORS basligi DONMEDIGI icin istek
// "Failed to fetch" ile COKTUGU olculdu. Ayrica bu desen zaten belgelenen
// guvenlik ilkesini (servis-proxy.ts: "Servis adresi YALNIZCA sunucuda
// okunur, NEXT_PUBLIC_ KULLANILMAZ") ihlal ediyordu - digerlerinin
// hicbirinde NEXT_PUBLIC_ ile dogrudan servis adresi yok. Bu route, PriceChart'i
// da ayni guvenli/tutarli kaliba tasir.
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const t = tickerDogrula(ticker)
  if (!t) return gecersizTicker()

  // `limit` ILETIMI (23.09.2026): daha once iletilmedigi icin grafik her zaman
  // yukari akisin varsayilani olan ~60 barla sinirliydi; 13F/kongre olaylari
  // bu pencerenin disina dustugunde marker'lar SESSIZCE kayboluyordu.
  // Dogrulama mantigi @/lib/grafik/veri-penceresi icinde saf tutuldu.
  const pencere = limitDogrula(req.nextUrl.searchParams.get('limit'))
  if (pencere.durum === 'gecersiz') {
    return NextResponse.json({ hata: `Gecersiz limit: ${pencere.sebep}` }, { status: 400 })
  }

  return servisProxy({
    taban: process.env.MARKET_DATA_URL || 'http://alphawise-market-data:8000',
    yol: `/price/${encodeURIComponent(t)}${limitSorguDizesi(pencere)}`,
    zamanAsimiMs: 30_000,
    servisAdi: 'Market Data',
    kimlik: istekKimligi(req),
  })
}
