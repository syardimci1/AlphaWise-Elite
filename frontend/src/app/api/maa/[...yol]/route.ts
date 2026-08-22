import { NextRequest, NextResponse } from 'next/server'
import http from 'node:http'

// MAA proxy — MAA'nin adresi SUNUCU TARAFINDA kalir, tarayiciya ASLA sizmaz.
// Dashboard bu route'u cagirir, dogrudan MAA servisine gitmez.
//
// GOD MODE ROUTE'UNDAN FARKI (bilincli tasarim karari):
// God Mode route'u tek bir endpoint'e proxy yaptigi icin dogal olarak dardir.
// MAA'nin ise cok sayida endpoint'i var ve MAA'da HICBIR kimlik dogrulamasi
// yok (ne admin key, ne oturum kontrolu). Bu yuzden ayni darligi saglamak
// icin BEYAZ LISTE kullanilir: yalnizca dashboard'un gercekten kullandigi 3
// yol gecer. Listede olmayan her istek 403 ile reddedilir — boylece bu proxy
// MAA'nin diger (ucretli LLM tuketen ya da veri yazan) endpoint'lerine acilan
// bir kapi haline GELMEZ.

// Ticker disaridan gelen tek serbest girdidir. Buyuk harf + rakam + nokta/tire
// ile sinirli; bu desen '/' ve '.' dizilimlerini reddettigi icin yol asimi
// (path traversal) daha ilk kapida engellenir.
const TICKER_DESENI = /^[A-Z0-9][A-Z0-9.-]{0,9}$/

// Tam olarak eslesmesi gereken sabit yollar
const SABIT_YOLLAR = new Set(['portfolio-signal/adaptive_rotation'])

// <onek>/<TICKER> bicimindeki yollar
const TICKER_ONEKLERI = new Set(['narrative-verified', 'memory'])

// Kullaniciya 504 donulecek sure. OLCUMLE belirlendi:
//   portfolio-signal : dogrudan cagride 87.4 sn; cron loglarinda 78-102 sn.
//   narrative-verified: MAA loglarindan iki canli olcum (22.08.2026):
//       1) Analyst 65.3 + Critic 42.7 + Master 103.3 + 2 retry (39.2+40.5) = 290.9 sn
//       2) Analyst 196.9 + Critic 19.5 + Master 59.3                       = 275.7 sn
//     Sureler cok oynak, cunku cascade.py her LLM cagrisina 30 sn veriyor ve
//     model yanit vermezse yedege geciyor. Node'un varsayilan
//     server.requestTimeout'u 300 sn oldugu icin bu deger 290 sn'nin uzerine
//     cikarilamaz — yani bu endpoint icin guvenilir bir senkron zaman asimi
//     degeri YOKTUR. Asagidaki ISLEM HAVUZU + SONUC ONBELLEGI tam olarak bu
//     yuzden var: 504 artik "harcanan kredi cope gitti" anlamina gelmiyor.
//   memory           : Cognee'nin anlamsal sorgusu. ILK SURUMDE 30 sn idi ve
//     bu YETERSIZDI — "hizli" VARSAYILMISTI ama olculdugunde cok oynak oldugu
//     goruldu: ayni ticker icin arka arkaya 3.0 / 3.8 / 5.6 / 14.9 / 30.1 sn.
//     Bir olcum tam 30.1 sn ile sinirin uzerine cikti ve cognee yeniden
//     baslatildiktan sonra dashboard gercekten 504 aldi. Gozlenen en kotu
//     durumun ~3 kati verildi. (Bu cagri dashboard'da fire-and-forget'tir;
//     yavaslamasi analizi bloklamaz, yalnizca hafiza panelini geciktirir.)
const ZAMAN_ASIMI_MS: Record<string, number> = {
  'narrative-verified': 290_000,
  memory: 90_000,
  'portfolio-signal': 180_000,
}

// ---------------------------------------------------------------------------
// ISLEM HAVUZU VE SONUC ONBELLEGI — "504 aldim ama kredi yandi" sorununun cozumu
// ---------------------------------------------------------------------------
// TESPIT EDILEN SORUN (canli olcum, 22.08.2026):
// Proxy 504 dondugunde MAA DURMUYOR. Istemci baglantisi kopsa bile uvicorn
// calisan coroutine'i iptal etmiyor; kaskad sonuna kadar gidiyor ve
// OpenRouter kredisi harcanmaya devam ediyor. Iki test arasinda bakiyenin
// kendiliginden 0.0069 USD azalmasi bunun kanitidir.
//
// NEDEN "ISTEGI IPTAL ET" COZUM DEGIL:
// AbortSignal yalnizca BIZIM soketimizi kapatir; MAA tarafindaki isi
// durdurmaz. Gercek iptal MAA'nin kendi kodunda (korunan dosya) yapilmali.
// Bu yuzden burada, proxy seviyesinde yapilabilecek en iyi cozum uygulandi:
// KREDI ZATEN HARCANDIYSA, SONUCU BOSA HARCATMA.
//
// IKI KATMAN:
//   1) ISLEM HAVUZU  — ayni ticker icin es zamanli ikinci bir istek geldiginde
//      MAA'ya IKINCI bir cagri ACILMAZ; ucusta olan isleme baglanilir.
//      Boylece iki kullanici (ya da sabirsiz bir kullanicinin ikinci tiklamasi)
//      krediyi iki kez harcatamaz.
//   2) SONUC ONBELLEGI — arka planda tamamlanan istek, kullanici 504 almis
//      olsa bile sonucu buraya yazar. Kullanici tekrar denediginde sonuc
//      ANINDA ve UCRETSIZ doner; harcanan kredi bosa gitmemis olur.
//
// Arka plan istegi kullanici zaman asimindan BAGIMSIZ olarak devam eder, ama
// sonsuza kadar degil: DIS_SINIR_MS'de sert olarak kesilir, boylece asili
// kalan bir MAA istegi soket/bellek sizdiramaz.
const SONUC_TTL_MS = 15 * 60 * 1000 // tamamlanan sonuc 15 dk servis edilir

// Arka plan istegi icin mutlak ust sinir.
// DIKKAT — BU DEGER OLCUMLE BULUNDU, TAHMINLE DEGIL:
// Ilk surumde 600 sn (10 dk) idi ve BU BIR HATAYDI. Canli testte MSFT
// kaskadi 600 sn'de kesildi ama MAA 700. saniyede bitiyordu; kesilen istek
// reddedildigi icin sonuc ONBELLEGE HIC YAZILMADI — yani harcanan kredi yine
// bosa gitti, mekanizmanin butun amaci bosa cikti.
// Olculen gercek kaskad sureleri (MAA logu, 22.08.2026):
//   214.4 + 18.5 + 187.1 retry = 420 sn  (en kotu gozlem)
//   301.3 + 46.0 retry         = 347 sn
//   303.7 sn
// Tek bir "retry_duzeltme" adiminin 187 sn surebildigi goruldu; degiskenlik
// cok yuksek. Bu yuzden ust sinir en kotu gozlemin ~3 katina (20 dk)
// cikarildi. Bu deger bir performans hedefi DEGIL, yalnizca asili kalan bir
// istegin soket/bellek sizdirmasini onleyen son emniyet valfidir.
const DIS_SINIR_MS = 1_200_000
const ONBELLEK_AZAMI_KAYIT = 50 // bellek guvenligi

type SonucKaydi = { veri: any; zaman: number }

const SONUC_ONBELLEGI = new Map<string, SonucKaydi>()
const ISLEM_HAVUZU = new Map<string, Promise<any>>()

// Bu mekanizma yalnizca PAHALI/YAVAS yollar icin gerekli. memory hizli ve
// ucretsiz oldugu icin dahil edilmedi — gereksiz bellek tutmaz.
const HAVUZLANAN_YOLLAR = new Set(['narrative-verified', 'portfolio-signal'])

function onbellegiTemizle() {
  const simdi = Date.now()
  for (const [k, v] of SONUC_ONBELLEGI) {
    if (simdi - v.zaman > SONUC_TTL_MS) SONUC_ONBELLEGI.delete(k)
  }
  // TTL'e ragmen buyuduyse en eskiyi at (sert ust sinir)
  while (SONUC_ONBELLEGI.size > ONBELLEK_AZAMI_KAYIT) {
    const enEski = SONUC_ONBELLEGI.keys().next().value
    if (enEski === undefined) break
    SONUC_ONBELLEGI.delete(enEski)
  }
}

// NEDEN fetch DEGIL node:http (CANLI TESTLE BULUNAN HATA, 22.08.2026):
// Node'un yerlesik fetch'i (undici) yanit BASLIKLARI icin sabit 300 sn'lik
// bir ic zaman asimina sahiptir (headersTimeout) ve AbortSignal.timeout
// bunu UZATAMAZ. MAA'nin kaskadi 300 sn'yi rutin olarak astigi icin
// (olculen: 623 sn, 990 sn) arka plan fetch'i her seferinde 5. dakikada
// sessizce oluyor, havuz kaydi temizleniyor ve bir sonraki kullanici
// yoklamasi YENI bir kaskad baslatiyordu — mekanizma kredi israfini
// onlemek yerine KATLIYORDU (canli testte ayni ticker icin 3 kaskad
// gozlemlendi: 02:57, 03:04, 03:09). node:http istemcisinin boyle bir
// varsayilan sinir yoktur; tek sinir bizim DIS_SINIR_MS'imizdir.
function _httpGetJson(url: string, zamanAsimiMs: number): Promise<any> {
  return new Promise((cozumle, reddet) => {
    const istek = http.get(url, (yanit) => {
      const parcalar: Buffer[] = []
      yanit.on('data', (p) => parcalar.push(p))
      yanit.on('end', () => {
        const ham = Buffer.concat(parcalar).toString('utf8')
        let veri: any
        try {
          veri = JSON.parse(ham)
        } catch {
          const e: any = new Error('MAA servisi beklenmeyen (JSON olmayan) bir yanit dondurdu')
          e.httpKodu = 502
          return reddet(e)
        }
        const kod = yanit.statusCode ?? 0
        if (kod < 200 || kod >= 300) {
          const e: any = new Error(veri.detail || veri.error || 'MAA servisi hata dondurdu')
          e.httpKodu = kod
          return reddet(e)
        }
        cozumle(veri)
      })
      yanit.on('error', reddet)
    })
    // Soket kurulumundan yanit sonuna kadar TEK mutlak sinir.
    const sayac = setTimeout(() => {
      istek.destroy(new Error(`MAA istegi dis sinira ulasti (${zamanAsimiMs / 1000} sn)`))
    }, zamanAsimiMs)
    istek.on('error', (e) => {
      clearTimeout(sayac)
      reddet(e)
    })
    istek.on('close', () => clearTimeout(sayac))
  })
}

/** MAA'ya tek bir cagri acar; ayni anahtar icin ikinci cagri ACMAZ. */
function havuzdanGetir(anahtar: string, url: string): Promise<any> {
  const mevcut = ISLEM_HAVUZU.get(anahtar)
  if (mevcut) return mevcut

  const sozu = _httpGetJson(url, DIS_SINIR_MS)

  ISLEM_HAVUZU.set(anahtar, sozu)

  // Kullanici 504 alip gitmis olsa bile sonucu sakla — kredi bosa gitmesin.
  // .catch ZORUNLU: kullanicinin yarisi bittikten sonra bu soz reddedilirse
  // Node "unhandled rejection" ile sureci dusurebilir.
  sozu
    .then((veri) => {
      onbellegiTemizle()
      SONUC_ONBELLEGI.set(anahtar, { veri, zaman: Date.now() })
    })
    .catch(() => {
      /* hata onbellege YAZILMAZ: bir sonraki deneme temiz baslasin */
    })
    .finally(() => {
      ISLEM_HAVUZU.delete(anahtar)
    })

  return sozu
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ yol: string[] }> }
) {
  const { yol } = await params
  const maaUrl = process.env.MAA_URL || 'http://alphawise-maa:8000'

  if (!Array.isArray(yol) || yol.length === 0) {
    return NextResponse.json({ error: 'Eksik MAA yolu' }, { status: 400 })
  }

  const birlesikYol = yol.join('/')
  let hedefYol: string
  let zamanAsimiAnahtari: string

  if (SABIT_YOLLAR.has(birlesikYol)) {
    hedefYol = birlesikYol
    zamanAsimiAnahtari = yol[0]
  } else if (yol.length === 2 && TICKER_ONEKLERI.has(yol[0]) && TICKER_DESENI.test(yol[1])) {
    // encodeURIComponent ikinci koruma katmani: desen zaten dar, bu da
    // beklenmedik bir karakterin URL'ye ham gecmesini engeller.
    hedefYol = `${yol[0]}/${encodeURIComponent(yol[1])}`
    zamanAsimiAnahtari = yol[0]
  } else {
    // Sessizce basarisiz olma: neden reddedildigi acikca soylenir, ama
    // MAA'nin hangi endpoint'lerinin var oldugu bilgisi disari verilmez.
    return NextResponse.json(
      { error: 'Bu MAA yolu dashboard uzerinden kullanilamaz' },
      { status: 403 }
    )
  }

  const havuzlanir = HAVUZLANAN_YOLLAR.has(zamanAsimiAnahtari)
  const hedefUrl = `${maaUrl}/${hedefYol}`
  const kullaniciZamanAsimi = ZAMAN_ASIMI_MS[zamanAsimiAnahtari] ?? 30_000

  // 1) Tamamlanmis sonuc onbellekte mi? (504 sonrasi tekrar deneme buraya duser)
  if (havuzlanir) {
    onbellegiTemizle()
    const kayit = SONUC_ONBELLEGI.get(hedefYol)
    if (kayit) {
      return NextResponse.json({
        ...kayit.veri,
        _onbellekten: true,
        _onbellek_yasi_sn: Math.round((Date.now() - kayit.zaman) / 1000),
      })
    }
  }

  try {
    let veri: any
    if (havuzlanir) {
      // Arka plan istegi kullanici zaman asimindan BAGIMSIZ devam eder.
      const isSozu = havuzdanGetir(hedefYol, hedefUrl)
      let sayacId: any
      const zamanAsimiSozu = new Promise((_, red) => {
        sayacId = setTimeout(() => {
          const e: any = new Error('kullanici zaman asimi')
          e.kullaniciZamanAsimi = true
          red(e)
        }, kullaniciZamanAsimi)
      })
      try {
        veri = await Promise.race([isSozu, zamanAsimiSozu])
      } finally {
        clearTimeout(sayacId)
      }
    } else {
      const resp = await fetch(hedefUrl, {
        signal: AbortSignal.timeout(kullaniciZamanAsimi),
      })
      const ham = await resp.text()
      try {
        veri = JSON.parse(ham)
      } catch {
        return NextResponse.json(
          { error: 'MAA servisi beklenmeyen (JSON olmayan) bir yanit dondurdu' },
          { status: 502 }
        )
      }
      if (!resp.ok) {
        return NextResponse.json(
          { error: veri.detail || veri.error || 'MAA servisi hata dondurdu' },
          { status: resp.status }
        )
      }
    }
    return NextResponse.json(veri)
  } catch (err: any) {
    if (err?.kullaniciZamanAsimi) {
      // ONEMLI: analiz IPTAL EDILMEDI, arka planda suruyor. Kullaniciya
      // bunu acikca soyluyoruz ki tekrar denesin — tekrar denemede sonuc
      // onbellekten UCRETSIZ gelecek, kredi ikinci kez harcanmayacak.
      return NextResponse.json(
        {
          error:
            'Analiz beklenenden uzun suruyor ve arka planda devam ediyor. ' +
            'Birkac dakika sonra ayni hisse icin tekrar deneyin — sonuc ' +
            'hazirsa aninda gelecek, yeniden hesaplanmayacak.',
          _arka_planda_devam_ediyor: true,
        },
        { status: 504 }
      )
    }
    const zamanAsimiMi = err?.name === 'TimeoutError' || err?.name === 'AbortError'
    return NextResponse.json(
      {
        error: zamanAsimiMi
          ? 'MAA servisi zaman asimina ugradi (analiz beklenenden uzun surdu)'
          : err?.message || 'MAA servisine ulasilamiyor',
      },
      { status: err?.httpKodu ?? (zamanAsimiMi ? 504 : 502) }
    )
  }
}
