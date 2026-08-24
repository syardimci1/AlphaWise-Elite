import { NextRequest, NextResponse } from 'next/server'
import { oturumCereziVarMi, oturumDogrula } from '@/lib/oturum'

// ============================================================================
// HIZ SINIRLAMA (rate limiting) — 23.08.2026
//
// NEDEN: Denetimde olculdu — /api altindaki route'larin HICBIRINDE hiz
// sinirlamasi yoktu (o gun 13 route vardi; 24.08.2026 itibariyle 16). Canli kanit: 100 ardisik/es zamanli istek -> 100 x 200,
// tek bir 429 yok. En yuksek risk /api/maa/narrative-verified/<TICKER>:
// her cagri OpenRouter kredisi harciyor ve proxy 504 dondurse bile MAA
// kaskadi sonuna kadar gidip krediyi harcamaya devam ediyor.
//
// BU KATMAN NEYI SINIRLAR / NEYI SINIRLAMAZ:
//   SINIRLAR : kullanicidan/disaridan gelen HTTP istek SAYISINI (IP basina).
//   SINIRLAMAZ: ic servislerin dis saglayicilara olan kotalarini
//               (FMP, FlashAlpha, LLMQuant, SEC). Onlar AYRI bir katmandir
//               ve kendi servislerinde uygulanir (or. sec-edgar-13f-service/
//               src/rate_limiter.py giden yonde jeton kovasi, qlib'in FMP
//               kota bekcisi). Ikisi KARISTIRILMAMALIDIR.
//
// TASARIM KARARLARI:
//  * Yeni bagimlilik EKLENMEDI. frontend'de package-lock.json YOK ve
//    Dockerfile `npm install` calistiriyor; kayan surumlu bir kutuphane
//    eklemek her imaj yapiminda farkli cozulebilirdi. Bu yuzden saf TS
//    jeton kovasi yazildi.
//  * Sayac SUREC ICIDIR. Frontend tek konteyner/tek replika oldugu icin
//    bugun dogru calisir; konteyner yeniden baslarsa sayaclar sifirlanir ve
//    replika sayisi artarsa sinir replika BASINA uygulanir. Dagitik sayac
//    gerekirse alphawise-redis ayni agda hazir (yalnizca baglanti anahtari
//    tanimli degil) — bu bilinen ve belgelenmis sinirdir.
//  * Maliyet siniflarina gore KADEMELI sinir: kredi harcayan uc en dar,
//    salt okunur yerel uc en genis.
// ============================================================================
// 23.08.2026 EK: bu dosya artik SADECE hiz sinirlamasi yapmiyor; /api/*
// altindaki tum uclar icin OTURUM ZORUNLULUGUNU da burada uyguluyor
// (bkz. src/lib/oturum.ts). Tek noktadan uygulanmasinin nedeni: yeni bir
// route eklendiginde kimlik kontrolunun UNUTULAMAMASI.
// ============================================================================

type Kova = { jeton: number; sonDolum: number }

const KOVALAR = new Map<string, Kova>()
const MAKS_KOVA = 10_000            // bellek ust siniri (DoS'a karsi)
const TEMIZLIK_MS = 10 * 60 * 1000  // 10 dk'dan eski kovalar atilir
let sonTemizlik = Date.now()

// Sinif -> (dakikada izin verilen istek, ani patlama kapasitesi)
const SINIFLAR = {
  // Kredi harcar (OpenRouter/LLM). En dar sinir.
  pahali: { dakikada: 5, patlama: 5 },
  // Dis ucretsiz/kotali API'lere dokunur (SEC, FINRA, FMP, FlashAlpha).
  //
  // 23.08.2026 AYAR DUZELTMESI: ilk deger (30/dk, patlama 10) OLCULEREK
  // fazla dar bulundu. Dashboard'in NORMAL acilisi 9 sinyal kartini es
  // zamanli cagiriyor ve 10 jetonun 8'ini tuketiyordu (olculen kalan: 2).
  // Kullanici 20 saniye icinde iki kez yenilese KENDI dashboard'inda 429
  // alacakti. Patlama 20'ye cikarildi.
  //
  // 24.08.2026 IKINCI AYAR: iki yeni kart (FRED makro + Finnhub) eklendi,
  // dashboard acilisi artik 9 DEGIL 11 es zamanli istek yapiyor. Patlama
  // 20'de kalsaydi 20 saniye icindeki IKI yenileme 22 jeton isteyecek ve
  // kullanici yine KENDI dashboard'inda 429 alacakti — yani yeni kartlar
  // mevcut kartlari bozacakti. Tavan 35'e cikarildi: uc tam yenilemeye
  // (33 jeton) yer birakir, dakikalik 60 siniri ise DEGISMEDI, yani
  // kotuye kullanima karsi koruma ayni kaldi.
  sinyal: { dakikada: 60, patlama: 35 },
  // Yerel/ucuz: dosya listeleme, onbellekten okuma.
  ucuz: { dakikada: 120, patlama: 30 },
} as const

type Sinif = keyof typeof SINIFLAR

// 23.08.2026 GUVENLIK DUZELTMESI — yuzde-kodlama ile SINIF ATLATMA:
// Next.js App Router catch-all segmentlerini ([...yol]) route'a vermeden ONCE
// yuzde-cozer. Ilk surum ham pathname uzerinde duz metin karsilastirmasi
// yaptigi icin `/api/maa/narrative-%76erified` middleware'de 'sinyal'
// (60/dk) sayiliyor, route ise cozup GERCEK LLM kaskadini calistiriyordu —
// amaclanan 5/dk sinirinin 12 KATI. Canli olarak dogrulandi.
// Cozum: siniflandirmadan once yolu coz.
function yoluCoz(yol: string): string {
  let onceki = yol
  // Ic ice kodlamaya karsi (%2576 gibi) sabit noktaya kadar coz.
  for (let i = 0; i < 3; i++) {
    let cozulmus: string
    try {
      cozulmus = decodeURIComponent(onceki)
    } catch {
      return onceki // bozuk kodlama: ham hali kullan
    }
    if (cozulmus === onceki) return cozulmus
    onceki = cozulmus
  }
  return onceki
}

function sinifBelirle(yol: string): Sinif | null {
  if (!yol.startsWith('/api/')) return null
  // MAA'nin LLM ureten ucu — kredi harcar.
  if (yol.startsWith('/api/maa/narrative-verified')) return 'pahali'
  if (yol.startsWith('/api/maa/')) return 'sinyal'
  if (yol.startsWith('/api/raporlar')) return 'ucuz'
  return 'sinyal'
}

// 23.08.2026 — REDDEDILEN ISTEK JETON YAKMASIN:
// Sayac middleware'de dusuluyor, yani route'un 403 verdigi (MAA'ya hic
// ulasmayan) bir yol da jeton harciyordu. Tek ortak kova ile birlesince bu,
// hicbir maliyet odemeden urunun ana ozelligini kilitleyen bir hizmet
// engelleme yolu aciyordu. MAA beyaz listesi burada da uygulanir; beyaz
// liste disi yol JETON HARCAMADAN 403 alir (route ile ayni sonuc).
const MAA_BEYAZ_LISTE = [
  /^\/api\/maa\/portfolio-signal\/adaptive_rotation\/?$/,
  /^\/api\/maa\/narrative-verified\/[A-Z0-9]+(?:[.-][A-Z0-9]+)*$/i,
  /^\/api\/maa\/memory\/[A-Z0-9]+(?:[.-][A-Z0-9]+)*$/i,
]

function maaYoluGecerli(yol: string): boolean {
  if (!yol.startsWith('/api/maa/')) return true
  return MAA_BEYAZ_LISTE.some(d => d.test(yol))
}

// X-Forwarded-For'a GUVENILIR MI?
//
// 23.08.2026 GUVENLIK DUZELTMESI: ilk surum bu basligi kosulsuz okuyordu.
// Onunde ters vekil OLMAYAN bir uygulamada bu basligi ISTEMCI gonderir ve
// tamamen taklit edilebilir: saldirgan her istekte farkli bir deger yazarak
// her seferinde YENI ve DOLU bir kova alir, yani sinir tamamen etkisiz kalir.
// Denetimde olculdu: su an /etc/nginx yok, caddy/traefik yok, frontend
// dogrudan 127.0.0.1:3000'e bagli — yani GUVENILIR BIR VEKIL YOK.
//
// Varsayilan: basliga GUVENME. Ileride onune gercek bir ters vekil konursa
// GUVENILIR_VEKIL=1 ortam degiskeni ile acilir.
const VEKILE_GUVEN = process.env.GUVENILIR_VEKIL === '1'

function istemciKimligi(req: NextRequest): string {
  if (VEKILE_GUVEN) {
    const xff = req.headers.get('x-forwarded-for')
    if (xff) return xff.split(',')[0].trim()
    const xri = req.headers.get('x-real-ip')
    if (xri) return xri
  }
  // Guvenilir vekil yokken TEK ortak kova kullanilir. Bu, taklit edilemez;
  // bedeli, ayni anda birden fazla mesru kullanici varsa sinirin ortak
  // olmasidir. Servis su an yalnizca 127.0.0.1'e bagli oldugu icin
  // (disaridan erisim SSH tuneli gerektiriyor) bu kabul edilebilir bir
  // dengedir ve taklit edilebilir bir sinirdan DAHA GUCLUDUR.
  return 'ortak'
}

function temizle(simdi: number) {
  if (simdi - sonTemizlik < TEMIZLIK_MS) return
  sonTemizlik = simdi
  for (const [k, v] of KOVALAR) {
    if (simdi - v.sonDolum > TEMIZLIK_MS) KOVALAR.delete(k)
  }
}

function izinVar(anahtar: string, sinif: Sinif, simdi: number) {
  const { dakikada, patlama } = SINIFLAR[sinif]
  const oranSaniyede = dakikada / 60
  let kova = KOVALAR.get(anahtar)
  if (!kova) {
    // 23.08.2026 DUZELTME: burada kosulsuz `izin: true` vardi (fail-open).
    // Harita dolunca yeni her anahtar SAYILMADAN geciyordu — GUVENILIR_VEKIL
    // acilirsa dogrudan bir sinir atlatma yoluna donusurdu. Ayrica buradaki
    // temizle() cagrisi OLU KOD'du: middleware() zaten ayni `simdi` degeriyle
    // temizle() cagirdigi icin ic kontrol her zaman erken donuyordu.
    // Artik FAIL-CLOSED: harita doluysa istek reddedilir.
    if (KOVALAR.size >= MAKS_KOVA) {
      return { izin: false, kalan: 0, bekle: 60 }
    }
    kova = { jeton: patlama, sonDolum: simdi }
    KOVALAR.set(anahtar, kova)
  }
  const gecen = (simdi - kova.sonDolum) / 1000
  kova.jeton = Math.min(patlama, kova.jeton + gecen * oranSaniyede)
  kova.sonDolum = simdi
  if (kova.jeton >= 1) {
    kova.jeton -= 1
    return { izin: true, kalan: Math.floor(kova.jeton), bekle: 0 }
  }
  const bekle = Math.ceil((1 - kova.jeton) / oranSaniyede)
  return { izin: false, kalan: 0, bekle }
}

// Kimlik dogrulanamadiginda donen ortak yanit. Sebep DISARIYA ayrintili
// verilmez ("cerez yok" ile "jeton gecersiz" ayrimi saldirgana bilgi olur);
// ayrintili sebep yalnizca X-Oturum basliginda teshis icin tutulur.
function kimlikReddi(sebep: string) {
  return NextResponse.json(
    { hata: 'Kimlik dogrulanamadi', detay: 'Bu uc icin oturum acmis olmalisiniz.' },
    { status: 401, headers: { 'X-Oturum': sebep } },
  )
}

export async function middleware(req: NextRequest) {
  const yol = yoluCoz(req.nextUrl.pathname)
  const sinif = sinifBelirle(yol)
  if (!sinif) return NextResponse.next()

  const simdi = Date.now()
  temizle(simdi)
  const anahtar = `${istemciKimligi(req)}|${sinif}`
  // 23.08.2026: beyaz liste disi MAA yolu JETON HARCAMADAN reddedilir.
  if (!maaYoluGecerli(yol)) {
    return NextResponse.json(
      { hata: 'Bu MAA yolu dashboard uzerinden kullanilamaz' },
      { status: 403 },
    )
  }

  // --- KIMLIK, ADIM 1/2: cerez var mi? (bedava, aga cikmaz, jeton yakmaz) ---
  // Sirasi bilincli: kimliksiz istek sunucumuza tek bir HTTP cagrisi bile
  // yaptirmadan, ayrica hiz sinirlama jetonu da harcamadan reddedilir.
  // Jeton harcatmamasi onemli: aksi halde kimliksiz bir sel, ortak kovayi
  // bosaltip MESRU kullaniciyi kilitleyen bir hizmet engellemeye donusurdu
  // (ayni tuzak MAA beyaz listesinde de bulunup duzeltilmisti).
  if (!oturumCereziVarMi(req)) return kimlikReddi('cerez_yok')

  const { izin, kalan, bekle } = izinVar(anahtar, sinif, simdi)
  // 23.08.2026: X-RateLimit-Limit `dakikada` degerini bildiriyordu ama ANLIK
  // tavan `patlama`; istemci Limit=60 / Remaining=19 gibi tutarsiz bir cift
  // goruyordu. Ikisi de ayri ayri bildirilir.
  const limit = SINIFLAR[sinif].dakikada
  const anlikTavan = SINIFLAR[sinif].patlama

  if (!izin) {
    return NextResponse.json(
      {
        hata: 'Cok fazla istek',
        detay:
          `Bu uc icin dakikada en fazla ${limit} istek (anlik patlama tavani ` +
          `${anlikTavan}) yapilabilir. ${bekle} saniye sonra tekrar deneyin.`,
        sinif,
      },
      {
        status: 429,
        headers: {
          'Retry-After': String(bekle),
          'X-RateLimit-Limit': String(limit),
          'X-RateLimit-Anlik-Tavan': String(anlikTavan),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Sinif': sinif,
        },
      },
    )
  }

  const yanit = NextResponse.next()

  // --- KIMLIK, ADIM 2/2: jetonu Supabase'e DOGRULAT ---
  // Cerezin varligi yetmez; cerez istemci tarafindan yazilabilir. Imza ve
  // sure kontrolu kimlik sunucusunda yapilir. Hiz sinirlamasindan SONRA
  // gelir, cunku bu adim ag cagrisi yapar ve sinirsiz tekrarlanmamalidir.
  const oturum = await oturumDogrula(req, yanit)
  if (!oturum.gecerli) return kimlikReddi(oturum.sebep)

  yanit.headers.set('X-RateLimit-Limit', String(limit))
  yanit.headers.set('X-RateLimit-Anlik-Tavan', String(anlikTavan))
  yanit.headers.set('X-RateLimit-Remaining', String(kalan))
  yanit.headers.set('X-RateLimit-Sinif', sinif)
  return yanit
}

export const config = {
  matcher: '/api/:path*',
}
