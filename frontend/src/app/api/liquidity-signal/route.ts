import { servisProxy } from '@/lib/servis-proxy'

// Liquidity Signal — Fed likidite rejimi (WALCL / TGA / RRP).
//
// Hisseye bagli DEGILDIR; bu yuzden [ticker] segmenti yoktur, /regime
// endpoint'i tum piyasa icin tek bir rejim degerlendirmesi dondurur.
//
// DURUM NOTU (22.08.2026 canli olcum): Servisin kendi /health yaniti
// "olgunluk: deneysel", "kalibrasyon_gecerli: false", "buzusme_lambda: 0.0"
// diyor; denenen 9 spesifikasyondan 0 tanesi gecme esigini (+5.0 puan)
// asmis (en iyi olculen beceri +1.63, en dusuk p=0.077). Servis bu yuzden
// yon iddiasi tasiyan kodlari (EKLE / DIKKAT ET) URETMEZ. Dashboard bu
// uyariyi one cikararak gosterir — sinyal yalnizca baglam/izleme amaclidir.
export async function GET() {
  return servisProxy({
    taban: process.env.LIQUIDITY_SIGNAL_URL || 'http://alphawise-liquidity-signal:8000',
    yol: '/regime',
    zamanAsimiMs: 45_000,
    servisAdi: 'Likidite Rejimi',
  })
}
