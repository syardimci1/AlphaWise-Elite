import { NextRequest, NextResponse } from 'next/server'
import { istekKimligi } from '@/lib/servis-proxy'

// Cagiran kullanicinin KENDI kimligini dondurur.
//
// NEDEN GEREKLI: kiraci kimligi yalnizca SUNUCUDA bilinir - middleware her
// /api istegine KULLANICI_BASLIGI'ni yazar, tarayicida ise yalnizca opak bir
// oturum cerezi vardir. Grafik terminali cizimleri localStorage'a
// `alphawise:grafik:cizim:v1:<kullanici>:<SEMBOL>` anahtariyla yaziyor
// (ADR-2) ve bu ad alanini kurabilmek icin istemcinin kendi kimligini
// bilmesi gerekiyor. Ortak bir tarayicida ad alani olmasaydi bir kullanicinin
// cizimleri digerine gorunurdu.
//
// SIZINTI YOK: yalnizca CAGIRANIN KENDI kimligi doner, baskasininki degil.
// Uc, middleware matcher'i `/api/:path*` altindadir; kimliksiz istek
// middleware tarafindan 401 ile reddedilir (bu route'a hic ulasmaz).
export async function GET(req: NextRequest) {
  const kimlik = istekKimligi(req)
  if (kimlik === null) {
    // Savunma amacli: normalde middleware kimliksiz istegi zaten durdurur.
    // Buraya ulasildiysa sessizce bos kimlik uydurmak (Y3) yerine acikca
    // hata donuyoruz - cagiran "kimlik yok" ile "kimlik bos" ayrimini gorur.
    return NextResponse.json({ hata: 'Kimlik okunamadi' }, { status: 401 })
  }
  return NextResponse.json(
    { kullaniciId: kimlik.kullaniciId, kiraci: kimlik.kiraci },
    { headers: { 'Cache-Control': 'no-store' } }
  )
}
