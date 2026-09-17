import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import {
  KULLANICI_BASLIGI,
  KIRACI_BASLIGI,
  kimlikOku,
  type Kimlik,
} from './kiraci'

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

// Ticker = harf/rakam bloklari, aralarinda TEK bir nokta veya tire.
//
// 23.08.2026 DUZELTME: onceki desen /^[A-Z0-9][A-Z0-9.-]{0,9}$/ idi ve ilk
// karakterden sonra ardisik noktalara izin veriyordu; 'A..', 'A.', 'A--B',
// 'A.B.' gibi bozuk semboller yukari servislere gidiyordu. ('../' zaten
// reddediliyordu, yani yol asimi acigi DEGILDI; sorun bozuk sembolun
// SEC/FINRA gibi dis kaynaklara iletilmesiydi.)
//
// REGRESYON KANITI: yeni desen, qlib deposundaki 6.755 gercek ABD
// hissesinin 6.755'ini de kabul ediyor (sifir kayip); BRK.B, BF-B, RDS.A
// gibi ozel bicimler korunuyor. Yalnizca bozuk diziler reddediliyor.
const TICKER_DESENI = /^[A-Z0-9]+(?:[.-][A-Z0-9]+)*$/
const TICKER_MAKS_UZUNLUK = 10

export function tickerDogrula(ham: string): string | null {
  const t = (ham || '').toUpperCase()
  if (t.length === 0 || t.length > TICKER_MAKS_UZUNLUK) return null
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
  /**
   * Cagiran kullanicinin kimligi (middleware'in yazdigi baslıktan okunur).
   *
   * OPSIYONEL VE BILINCLI: verilmezse davranis BUGUNKU gibi kalir. Boylece
   * 16 cagri noktasi tek tek guncellenirken sistem her adimda calisir
   * durumda olur (Y6).
   */
  kimlik?: Kimlik
}

/**
 * Rota fonksiyonundaki istekten kiraci kimligini okur.
 *
 * TAKLIT SINIRI: bu fonksiyon "middleware yazdi" ile "istemci gonderdi"
 * ayrimini YAPAMAZ. Koruma tamamen middleware'in HER /api yolunda gelen
 * basligi silip kendi degerini yazmasina baglidir (bkz. kiraci.ts guven
 * modeli ve middleware'deki basliklariTemizle cagrisi).
 */
export function istekKimligi(req: NextRequest | Request): Kimlik | null {
  return kimlikOku(req.headers)
}

// Yukari akis hata govdesinden kullaniciya GECIRILEBILECEK alanlar.
// IZIN LISTESI (kara liste degil): yeni bir servis yeni bir alan eklerse
// varsayilan olarak GECMEZ. Olculen sizinti tam olarak bu yuzden onemliydi —
// gamma-exposure detail'i "anahtar": "FLASHALPHA_API_KEY_2" ve TUM
// cagiranlarin ortak "kullanilan" sayacini tasiyordu.
const DETAY_IZIN_LISTESI = ['hata', 'aciklama', 'mesaj'] as const

/**
 * Yukari akis `detail` alanini kiraciya gore suzer.
 *
 * NEDEN: olculdu (16.09.2026) —
 *  - gamma-exposure-service/main.py:223,257 detail icinde kota_durumu()
 *    donduruyor; o da tek_anahtar_kota_durumu()'ndan gelen
 *    {"anahtar": "FLASHALPHA_API_KEY_2", "kullanilan": N} kayitlarini tasiyor.
 *    "anahtar" bir SIR ADI, "kullanilan" ise TUM kiracilarin ortak tuketimi —
 *    yani B, A'nin ne kadar harcadigini olcebilir (yan kanal).
 *  - finra-darkpool-service/src/main.py:49,71,97,140 detail=f"{type(e).__name__}: {e}"
 *    ile ic istisna metnini tasiyor.
 *  - dashboard/page.tsx:334-339 bu degeri JSON.stringify ile EKRANA basiyor.
 *
 * DAVRANIS: kimlik yoksa ya da kiraci 'sistem' ise BUGUNKU davranis aynen
 * surer (geriye uyumluluk + ic teshis). 'kullanici' ise izin listesi uygulanir.
 */
export function detayiSuz(detay: unknown, kimlik?: Kimlik): string | null {
  if (!kimlik || kimlik.kiraci !== 'kullanici') {
    return (typeof detay === 'string' ? detay : (detay as any) ?? null) as any
  }
  if (typeof detay === 'string') return detay.slice(0, 300)
  if (!detay || typeof detay !== 'object') return null
  const kaynak = detay as Record<string, unknown>
  const parcalar = DETAY_IZIN_LISTESI
    .map(a => kaynak[a])
    .filter((v): v is string => typeof v === 'string' && v.length > 0)
  if (parcalar.length === 0) return null
  return parcalar.join(' — ').slice(0, 300)
}

/**
 * Ham detayi SUNUCU gunlugune yazar — teshis yetenegi kaybolmaz, YER DEGISTIRIR.
 * Kullaniciya gitmeyen bilgi buradan okunabilir kalir.
 */
function hamDetayiGunlukle(servisAdi: string, kimlik: Kimlik | undefined, ham: unknown) {
  const kiraci = kimlik ? `${kimlik.kiraci}:${kimlik.kullaniciId}` : 'kimliksiz'
  try {
    console.warn(`[proxy:${servisAdi}] kiraci=${kiraci} ham_detay=`,
      typeof ham === 'string' ? ham.slice(0, 500) : JSON.stringify(ham)?.slice(0, 500))
  } catch {
    console.warn(`[proxy:${servisAdi}] kiraci=${kiraci} ham_detay=<serilestirilemedi>`)
  }
}

export async function servisProxy({
  taban,
  yol,
  zamanAsimiMs,
  servisAdi,
  kimlik,
}: ProxySecenek): Promise<NextResponse> {
  try {
    // Kimlik varsa yukari akisa TASINIR. Deger kiraci.ts'te dogrulanmis
    // oldugu icin (UUID ya da 'sistem') baslik degeri olarak guvenlidir —
    // CR/LF enjeksiyonu ya da undici TypeError'u mumkun degildir.
    const basliklar: Record<string, string> = kimlik
      ? { [KULLANICI_BASLIGI]: kimlik.kullaniciId, [KIRACI_BASLIGI]: kimlik.kiraci }
      : {}
    const yanit = await fetch(`${taban}${yol}`, {
      signal: AbortSignal.timeout(zamanAsimiMs),
      headers: basliklar,
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
      if (kimlik?.kiraci === 'kullanici') hamDetayiGunlukle(servisAdi, kimlik, detay)
      return NextResponse.json(
        {
          hata: `${servisAdi} veri dondurmedi`,
          servis_kodu: yanit.status,
          detay: detayiSuz(detay, kimlik),
        },
        { status: yanit.status }
      )
    }

    return NextResponse.json(veri)
  } catch (err: any) {
    const zamanAsimiMi =
      err?.name === 'TimeoutError' || err?.name === 'AbortError'
    // err.message IC ADRES VE PORT tasiyor ("connect ECONNREFUSED
    // 172.18.0.7:8000"). Bu metnin son kullaniciya bilgi degeri SIFIR,
    // saldirgana ag haritasi degeri yuksektir. Kullanici kiracisinda
    // tamamen bastirilir; ham metin sunucu gunlugune yazilir.
    if (!zamanAsimiMi && kimlik?.kiraci === 'kullanici') {
      hamDetayiGunlukle(servisAdi, kimlik, err?.message ?? String(err))
    }
    const detay = zamanAsimiMi
      ? null
      : kimlik?.kiraci === 'kullanici'
        ? null
        : err?.message ?? null
    return NextResponse.json(
      {
        hata: zamanAsimiMi
          ? `${servisAdi} zaman asimina ugradi`
          : `${servisAdi} servisine ulasilamiyor`,
        detay,
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
