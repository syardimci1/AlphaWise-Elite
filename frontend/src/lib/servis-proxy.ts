import { NextResponse } from 'next/server'

// Piyasa sinyali servisleri icin ORTAK sunucu tarafi proxy yardimcisi.
//
// NEDEN ORTAK BIR YARDIMCI:
// God Mode ve MAA route'lari tek servise proxy yaptigi icin mantiklarini
// kendi dosyalarinda tasiyor. Burada 7 servis var; ticker dogrulamasini ve
// hata yonetimini 7 kez kopyalamak, ileride birinde yapilan bir duzeltmenin
// digerlerinde unutulmasi demekti. Guvenlik kontrolu TEK YERDE toplanarak
// denetlenebilir tutuldu.
//
// GUVENLIK ILKELERI (God Mode route'uyla ayni):
//   1. Servis adresi YALNIZCA sunucuda, process.env uzerinden okunur.
//      NEXT_PUBLIC_ oneki KULLANILMAZ — o onek degeri tarayici paketine gomer.
//   2. Disaridan gelen tek serbest girdi olan ticker dar bir desene uyar;
//      desen '/' ve basta nokta kabul etmedigi icin yol asimi engellenir.
//   3. Servis hata verirse sessizce basarisiz OLUNMAZ; kullaniciya neden
//      veri gelmedigini soyleyen anlamli bir mesaj doner.

// Buyuk harf + rakam ile baslar; nokta ve tire yalnizca devaminda olabilir.
// Bu sayede '..' ve '../' gibi diziler daha ilk kapida reddedilir.
const TICKER_DESENI = /^[A-Z0-9][A-Z0-9.-]{0,9}$/

export function tickerDogrula(ham: string): string | null {
  const t = (ham || '').toUpperCase()
  return TICKER_DESENI.test(t) ? t : null
}

type ProxySecenek = {
  /** Servisin sunucu tarafi taban adresi (ornegin http://alphawise-qlib:8000) */
  taban: string
  /** Taban adresten sonraki yol (ornegin /predict/AAPL) */
  yol: string
  /** Bu servisin olculen yanit suresine gore secilmis zaman asimi */
  zamanAsimiMs: number
  /** Hata mesajlarinda gecen, kullanicinin anlayacagi servis adi */
  servisAdi: string
}

export async function servisProxy({
  taban,
  yol,
  zamanAsimiMs,
  servisAdi,
}: ProxySecenek): Promise<NextResponse> {
  try {
    const yanit = await fetch(`${taban}${yol}`, {
      signal: AbortSignal.timeout(zamanAsimiMs),
    })

    // Servisler her zaman JSON dondurmeyebilir (ornegin bir ag hatasinda
    // HTML hata sayfasi). Ham metni once okuyup cozmeyi deniyoruz ki
    // JSON.parse patlamasi kullaniciya bos ekran olarak yansimasin.
    const ham = await yanit.text()
    let veri: any
    try {
      veri = JSON.parse(ham)
    } catch {
      return NextResponse.json(
        { hata: `${servisAdi} beklenmeyen (JSON olmayan) bir yanit dondurdu` },
        { status: 502 }
      )
    }

    if (!yanit.ok) {
      // FastAPI hatalari {"detail": ...} icinde tasir; detail bazen metin,
      // bazen yapili bir nesne olur. Ikisini de kullaniciya tasiyoruz ki
      // "neden veri yok" sorusu cevapsiz kalmasin.
      const detay = veri?.detail ?? veri?.hata ?? veri?.error
      return NextResponse.json(
        {
          hata: `${servisAdi} veri dondurmedi`,
          servis_kodu: yanit.status,
          detay: typeof detay === 'string' ? detay : detay ?? null,
        },
        { status: yanit.status }
      )
    }

    return NextResponse.json(veri)
  } catch (err: any) {
    const zamanAsimiMi =
      err?.name === 'TimeoutError' || err?.name === 'AbortError'
    return NextResponse.json(
      {
        hata: zamanAsimiMi
          ? `${servisAdi} zaman asimina ugradi`
          : `${servisAdi} servisine ulasilamiyor`,
        detay: zamanAsimiMi ? null : err?.message ?? null,
      },
      { status: zamanAsimiMi ? 504 : 502 }
    )
  }
}

export function gecersizTicker(): NextResponse {
  return NextResponse.json(
    { hata: 'Gecersiz hisse kodu' },
    { status: 400 }
  )
}
