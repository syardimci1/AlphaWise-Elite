'use client'
// ============================================================================
// GRAFİK TERMİNALİ — çizim araçları + göstergeler + zaman dilimi orkestratörü
// ============================================================================
//
// BU BİLEŞEN BİLEREK İNCEDİR.
// Deponun test koşucusu çıplak `node:test`; jsdom YOKTUR, bu dosya render
// EDİLEMEZ. Dolayısıyla buraya konan her karar test edilemez bir karardır.
// Karar mantığının tamamı saf modüllerdedir ve orada sınanır:
//   - terminal-durum.ts   (araç/dilim/gösterge seçimi, tıklama akışı, metinler) 27 test
//   - cizim-model.ts      (çizim belgesi, geri al/yinele)                       — testli
//   - cizim-geometri.ts   (isabet, koordinat, görünüm)                          — testli
//   - gosterge-tanim.ts   (hangi gösterge neyi çizer)                           — testli
//   - zaman-dilimi.ts     (bar çevirme + resample)                              — testli
// Burada kalan yalnızca: kütüphane kurulumu, ağ çağrısı, DOM olayları ve
// yaşam döngüsü temizliği.
//
// NEDEN KENDİ GRAFİĞİNİ KURUYOR (PriceChart.tsx'i kullanmıyor):
// PriceChart başka sayfalarda kullanılıyor; çizim primitive'i, alt panel
// göstergeleri ve tıklama aboneliği eklemek onun sözleşmesini değiştirirdi.
// O dosyaya DOKUNULMADI.
//
// Y8 (HUKUKİ DİL): bu dosyada GÖRÜNEN sabit metin YOKTUR; hepsi
// `terminal-durum.ARAYUZ_METINLERI`'nden okunur ve orada yasaklı kalıp
// listesiyle test edilir. Metni buraya gömmek kapıyı atlamak olurdu.
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { CandlestickSeries, ColorType, createChart } from 'lightweight-charts'
import type { CandlestickData, IChartApi, ISeriesApi, MouseEventParams, Time } from 'lightweight-charts'
import { utcMsToIsGunuString, gunStringindenUtcMs } from '@/lib/koyfin-zaman'
import type { Nokta } from '@/lib/grafik/cizim-model'
import { bosDurum, reducer as cizimReducer } from '@/lib/grafik/cizim-model'
import type { Donusum } from '@/lib/grafik/cizim-geometri'
import { enYakinCizim } from '@/lib/grafik/cizim-geometri'
import { CizimPrimitive } from '@/lib/grafik/cizim-primitive'
import { GostergeKatmani } from '@/lib/grafik/gosterge-katmani'
import { GOSTERGE_TANIMLARI, tumGostergeKimlikleri } from '@/lib/grafik/gosterge-tanim'
import type { Depo } from '@/lib/grafik/cizim-kalicilik'
import { kaydet, yukle } from '@/lib/grafik/cizim-kalicilik'
import { gostergeAnahtari, gostergeleriKaydet, gostergeleriYukle } from '@/lib/grafik/gosterge-kalicilik'
import type { Bar } from '@/lib/grafik/zaman-dilimi'
import { hamBarlariCevir, resample } from '@/lib/grafik/zaman-dilimi'
import type { CizimKimligi, TerminalDurum, TerminalEylem } from '@/lib/grafik/terminal-durum'
import {
  ARAC_ETIKETLERI,
  ARAC_SIRASI,
  ARAYUZ_METINLERI,
  DILIM_ETIKETLERI,
  DILIM_SIRASI,
  GUN_ICI_DILIMLER,
  bosTerminalDurum,
  dilimEtiketi,
  gunIciNeden,
  terminalReducer,
  tiklamaSonucu,
  veriNotu,
  yuklemeNotu,
} from '@/lib/grafik/terminal-durum'

type Props = {
  symbol: string
  /**
   * Çizimlerin localStorage ad alanını kuran kullanıcı kimliği (ADR-2).
   *
   * OPSİYONEL VE BİLİNÇLİ: kiracı kimliği yalnızca SUNUCUDA bilinir —
   * middleware her /api isteğine yazar, tarayıcıda yalnızca opak bir oturum
   * çerezi vardır. Bu yüzden verilmezse bileşen kimliği kendisi
   * `/api/config/kimlik` ucundan çeker. Böylece çağıran sayfanın (dashboard)
   * kimlik çekme sorumluluğu YOKTUR ve o dosyadaki değişiklik üç satırda kalır
   * — paylaşılan bir dosyada komşu oturumla çakışma yüzeyi küçülür (Y16).
   */
  kullaniciKimligi?: string
}

/** Bayrak yanıtı gelene kadar bileşen HİÇBİR ŞEY çizmez (Y7: varsayılan kapalı). */
type BayrakDurumu = 'bekliyor' | 'acik' | 'kapali'

const RENK = {
  yuzey: '#1e293b',
  cizgi: '#334155',
  vurgu: '#D4AF37',
  metin: '#e2e8f0',
  ikincil: '#94a3b8',
  soluk: '#64748b',
  hata: '#f87171',
}

/** Yeni çizimlerin sabit stili. Renk seçici istenmedi; tek kaynakta tutuluyor. */
const CIZIM_STILI = { renk: RENK.vurgu, kalinlik: 2 }

/**
 * Çekilecek bar sayısı. Proxy `limit`i doğruluyor (veri-penceresi.ts: üst sınır
 * 2000); 1500 gün ≈ 6 yıl işlem günü, aylık dilimde de anlamlı bir seri bırakır.
 */
const BAR_LIMITI = 1500
const GRAFIK_YUKSEKLIGI = 420

function hataMetni(hata: unknown): string {
  return hata instanceof Error ? hata.message : String(hata)
}

/**
 * localStorage'a erişim, gizli sekmede/depolama kapalıyken PROPERTY okumasında
 * bile fırlatabilir. Hata yutulmaz, çağırana metin olarak taşınır (ADR-2).
 */
function depoAl(): { depo: Depo | null; hata: string | null } {
  try {
    return { depo: window.localStorage, hata: null }
  } catch (hata) {
    return { depo: null, hata: hataMetni(hata) }
  }
}

/**
 * Kütüphanenin `Time` birleşimini UTC ms'e indirger.
 *
 * Seri "YYYY-MM-DD" iş günü stringiyle besleniyor, yani pratikte yalnızca ilk
 * dal çalışır; diğer iki dal kütüphane sözleşmesinin tamamını karşılamak için
 * var — tip zorlaması ya da kaçış kullanmadan (Y13).
 */
function zamanUtcMs(zaman: Time | null | undefined): number | null {
  if (zaman === null || zaman === undefined) return null
  if (typeof zaman === 'string') {
    const ms = gunStringindenUtcMs(zaman)
    return Number.isFinite(ms) ? ms : null
  }
  // UTCTimestamp SANİYE cinsindendir; ms'e çevrilmezse tarih 1970'e düşerdi.
  if (typeof zaman === 'number') return zaman * 1000
  return Date.UTC(zaman.year, zaman.month - 1, zaman.day)
}

/** Grafik -> ekran dönüşümü; `cizim-geometri`nin beklediği arayüz. */
function donusumYap(grafik: IChartApi, seri: ISeriesApi<'Candlestick', Time>): Donusum {
  const olcek = grafik.timeScale()
  return {
    zamanX: (t_utc: number): number | null => olcek.timeToCoordinate(utcMsToIsGunuString(t_utc)),
    fiyatY: (fiyat: number): number | null => seri.priceToCoordinate(fiyat),
  }
}

export default function GrafikTerminali({ symbol, kullaniciKimligi }: Props) {
  const [bayrak, setBayrak] = useState<BayrakDurumu>('bekliyor')
  const [cekilenKimlik, setCekilenKimlik] = useState<string | null>(null)
  const [hata, setHata] = useState('')
  const [not, setNot] = useState('')
  const [yukleniyor, setYukleniyor] = useState(false)
  const [barlar, setBarlar] = useState<Bar[]>([])
  const [atlananHam, setAtlananHam] = useState(0)
  const [grafikHazir, setGrafikHazir] = useState(false)
  const [yuklenenSembol, setYuklenenSembol] = useState<string | null>(null)
  const [depoNotu, setDepoNotu] = useState('')
  /**
   * Gösterge seçiminin YÜKLENDİĞİ anahtar (ADR-5). Kaydetme yalnızca bu,
   * o anki kullanıcı+sembolün anahtarına eşitken yapılır: aksi halde önceki
   * sembolün/kullanıcının seçimi yeni ad alanına yazılırdı.
   */
  const [yuklenenGostergeAnahtari, setYuklenenGostergeAnahtari] = useState<string | null>(null)
  const [gostergeKayitHatasi, setGostergeKayitHatasi] = useState('')

  // NEDEN useReducer DEĞİL useState: tıklama akışında durumu üreten
  // `tiklamaSonucu` ZATEN tam bir `TerminalDurum` döndürür. useReducer ile
  // aynı sonuca varmak için o kararı eylem eylem yeniden kurmak gerekirdi ve
  // iki taraf sessizce ayrışabilirdi (saf modülün önlemek için var olduğu şey).
  // Düğmeler yine aynı saf reducer'dan geçer.
  const [terminal, setTerminal] = useState<TerminalDurum>(bosTerminalDurum)
  const terminalGonder = useCallback((eylem: TerminalEylem): void => {
    setTerminal((onceki) => terminalReducer(onceki, eylem))
  }, [])
  const [cizimDurum, cizimGonder] = useReducer(cizimReducer, undefined, bosDurum)

  const kutuRef = useRef<HTMLDivElement | null>(null)
  const grafikRef = useRef<IChartApi | null>(null)
  const seriRef = useRef<ISeriesApi<'Candlestick', Time> | null>(null)
  const primitiveRef = useRef<CizimPrimitive | null>(null)
  const katmanRef = useRef<GostergeKatmani | null>(null)
  /** Çizim kimliği sayacı: aynı milisaniyede iki çizim aynı id'yi almasın. */
  const sayacRef = useRef(0)

  // 1) Feature flag. Kapalıysa bileşen HİÇ render edilmez (Y7).
  useEffect(() => {
    let iptal = false
    fetch('/api/config/grafik-flag')
      .then(async (yanit) => {
        const govde: unknown = await yanit.json()
        const acik =
          typeof govde === 'object' && govde !== null && (govde as { enabled?: unknown }).enabled === true
        if (!iptal) setBayrak(acik ? 'acik' : 'kapali')
      })
      .catch((sebep: unknown) => {
        // FAIL-CLOSED ve GÖRÜNMEZ — bilinçli. Bayrak okunamadıysa özellik
        // AÇILMAZ; bileşen hiç render edilmediği için hata mesajını
        // basacak bir yüzey de yoktur. Kapalı bir özelliğin arıza kutusunu
        // göstermek, o özelliğin varlığını sızdırırdı. Aynı desen komşu
        // BildirimMerkezi.tsx'in 403 yolunda da uygulanıyor.
        //
        // Mesaj yine de saklanır: bayrak SONRADAN açılırsa (yeniden
        // bağlanma) ilk render'da görünür. Ekrana hiç çıkmaması bu
        // dosyanın değil, Y7'nin gereğidir.
        if (!iptal) {
          setBayrak('kapali')
          setHata(`${ARAYUZ_METINLERI.bayrakHatasi}: ${hataMetni(sebep)}`)
        }
      })
    return () => {
      iptal = true
    }
  }, [])

  // 1b) Kimlik. Prop verilmişse ağ isteği HİÇ yapılmaz.
  //
  // Bayrak AÇILANA KADAR beklenir: kapalı bir özellik için kimlik ucuna
  // istek atmak, özelliğin varlığını ağ trafiğinde sızdırırdı (Y7).
  useEffect(() => {
    if (bayrak !== 'acik') return
    if (kullaniciKimligi !== undefined) return
    let iptal = false
    fetch('/api/config/kimlik')
      .then(async (yanit) => {
        if (!yanit.ok) throw new Error(`HTTP ${yanit.status}`)
        const govde: unknown = await yanit.json()
        const kimlik =
          typeof govde === 'object' && govde !== null
            ? (govde as { kullaniciId?: unknown }).kullaniciId
            : undefined
        if (typeof kimlik !== 'string' || kimlik.length === 0) {
          throw new Error('kimlik alanı yok')
        }
        if (!iptal) setCekilenKimlik(kimlik)
      })
      .catch((sebep: unknown) => {
        // FAIL-CLOSED: kimlik yoksa çizimler YÜKLENMEZ ve KAYDEDİLMEZ.
        // Uydurma bir ad alanı ("anonim" gibi) kullanmak, ortak bir
        // tarayıcıda bir kullanıcının çizimlerini diğerine gösterirdi —
        // kiracı izolasyonu bu depoda sert bir ilkedir.
        if (!iptal) setHata(`${ARAYUZ_METINLERI.kimlikHatasi}: ${hataMetni(sebep)}`)
      })
    return () => {
      iptal = true
    }
  }, [bayrak, kullaniciKimligi])

  /** Etkin kimlik: prop öncelikli, yoksa uçtan çekilen. İkisi de yoksa null. */
  const etkinKimlik: string | null = kullaniciKimligi ?? cekilenKimlik

  // 2) Fiyat verisi. Ham yanıt saf `hamBarlariCevir` ile çevrilir; atlanan
  //    kayıt sayısı arayüze taşınır (sessiz kayıp yok).
  useEffect(() => {
    if (bayrak !== 'acik') return
    let iptal = false
    setYukleniyor(true)
    fetch(`/api/market-data/${encodeURIComponent(symbol)}?limit=${BAR_LIMITI}`)
      .then(async (yanit) => {
        if (!yanit.ok) throw new Error(`HTTP ${yanit.status}`)
        const govde: unknown = await yanit.json()
        if (iptal) return
        const cevrilen = hamBarlariCevir(govde)
        setBarlar(cevrilen.barlar)
        setAtlananHam(cevrilen.atlanan)
        setHata('')
      })
      .catch((sebep: unknown) => {
        if (!iptal) {
          setBarlar([])
          setHata(`${ARAYUZ_METINLERI.veriHatasi}: ${hataMetni(sebep)}`)
        }
      })
      .finally(() => {
        if (!iptal) setYukleniyor(false)
      })
    return () => {
      iptal = true
    }
  }, [bayrak, symbol])

  // Dilime indirgeme SAF ve ucuzdur; effect yerine türetilmiş değer olarak
  // hesaplanır — böylece etiket ile grafiğe basılan veri AYNI sonuçtan gelir.
  const dilimSonucu = useMemo(() => resample(barlar, terminal.dilim), [barlar, terminal.dilim])

  // 3) Grafik kurulumu. Yalnızca bayrak açıkken ve bir kez.
  useEffect(() => {
    if (bayrak !== 'acik') return
    const kutu = kutuRef.current
    if (kutu === null) return

    const grafik = createChart(kutu, {
      width: kutu.clientWidth,
      height: GRAFIK_YUKSEKLIGI,
      layout: { background: { type: ColorType.Solid, color: '#0f172a' }, textColor: RENK.metin },
      grid: { vertLines: { color: RENK.cizgi }, horzLines: { color: RENK.cizgi } },
    })
    const seri = grafik.addSeries(CandlestickSeries)
    const primitive = new CizimPrimitive()
    seri.attachPrimitive(primitive)
    const katman = new GostergeKatmani(grafik)

    grafikRef.current = grafik
    seriRef.current = seri
    primitiveRef.current = primitive
    katmanRef.current = katman
    setGrafikHazir(true)

    const boyutlandir = (): void => {
      if (kutuRef.current !== null) grafik.applyOptions({ width: kutuRef.current.clientWidth })
    }
    window.addEventListener('resize', boyutlandir)

    return () => {
      window.removeEventListener('resize', boyutlandir)
      setGrafikHazir(false)
      // SIRA ÖNEMLİ: katman ve primitive, grafik yok edilmeden ÖNCE
      // bırakılmalı (GostergeKatmani.temizle sözleşmesi). Ters sırada
      // kütüphane hata fırlatır.
      katman.temizle()
      seri.detachPrimitive(primitive)
      grafik.remove()
      grafikRef.current = null
      seriRef.current = null
      primitiveRef.current = null
      katmanRef.current = null
    }
  }, [bayrak])

  // 4) Mum verisi + göstergeler. Aynı effect: ikisi de aynı bar dizisinden
  //    beslenir, ayrı effect'lerde yarım kare boyunca uyumsuz kalabilirlerdi.
  useEffect(() => {
    if (!grafikHazir) return
    const grafik = grafikRef.current
    const seri = seriRef.current
    const katman = katmanRef.current
    if (grafik === null || seri === null || katman === null) return

    const mumlar: CandlestickData<Time>[] = dilimSonucu.barlar.map((bar) => ({
      time: bar.tarih,
      open: bar.acilis,
      high: bar.yuksek,
      low: bar.dusuk,
      close: bar.kapanis,
    }))
    seri.setData(mumlar)
    katman.uygula(
      terminal.gostergeler,
      dilimSonucu.barlar.map((bar) => bar.tarih),
      dilimSonucu.barlar.map((bar) => bar.kapanis),
    )
  }, [grafikHazir, dilimSonucu, terminal.gostergeler])

  // 4b) Görünümü sığdırma AYRI bir effect'te ve bağımlılıkları KASTEN dar.
  //
  // B1 (23.09.2026, bağımsız denetim bulgusu): `fitContent()` yukarıdaki
  // effect'in içindeydi ve o effect `terminal.gostergeler`'e de bağlıydı.
  // Sonuç: kullanıcı yakınlaştırıp kaydırdıktan sonra HERHANGİ bir gösterge
  // düğmesine bastığında görünüm tüm aralığa geri dönüyordu — sessiz ve
  // sinir bozucu bir veri kaybı (kullanıcının kurduğu görünüm).
  // Sığdırma YALNIZCA veri penceresi gerçekten değiştiğinde anlamlıdır:
  // sembol ya da zaman dilimi. Gösterge eklemek aynı barları gösterir.
  useEffect(() => {
    if (!grafikHazir) return
    const grafik = grafikRef.current
    if (grafik === null) return
    if (dilimSonucu.barlar.length === 0) return
    grafik.timeScale().fitContent()
  }, [grafikHazir, symbol, terminal.dilim])

  // 5) Kayıtlı çizimleri yükle. Sembol ya da kullanıcı değişince yeniden.
  useEffect(() => {
    if (bayrak !== 'acik') return
    // Kimlik gelmeden yükleme YAPILMAZ: kimliksiz bir ad alanı uydurmak,
    // ortak bir tarayıcıda başkasının çizimlerini göstermek demekti.
    if (etkinKimlik === null) return
    const { depo, hata: depoHatasi } = depoAl()
    if (depo === null) {
      setDepoNotu(`${ARAYUZ_METINLERI.kayitHatasi}: ${depoHatasi ?? ''}`)
      setYuklenenSembol(symbol)
      return
    }
    const sonuc = yukle(depo, etkinKimlik, symbol)
    cizimGonder({ tip: 'YUKLE', cizimler: sonuc.cizimler })
    // Göstergeler de aynı anda, aynı ad alanından (ADR-5). Kaydı olmayan
    // sembol boş seçimle açılır: seçim sembole aittir, sembolden sembole taşınmaz.
    const gostergeSonucu = gostergeleriYukle(depo, etkinKimlik, symbol)
    terminalGonder({ tip: 'GOSTERGELERI_YUKLE', gostergeler: gostergeSonucu.gostergeler })
    setYuklenenGostergeAnahtari(gostergeAnahtari(etkinKimlik, symbol))
    setDepoNotu(yuklemeNotu(sonuc.uyari, gostergeSonucu.uyari) ?? '')
    setYuklenenSembol(symbol)
  }, [bayrak, symbol, etkinKimlik, terminalGonder])

  // 6) Çizim değişince kaydet. YÜKLEME BİTMEDEN yazılmaz: aksi halde boş
  //    başlangıç durumu, kayıtlı çizimlerin üzerine yazılırdı.
  useEffect(() => {
    if (bayrak !== 'acik' || yuklenenSembol !== symbol) return
    // Kimlik yoksa KAYDEDİLMEZ (yüklemeyle simetrik): yanlış ad alanına
    // yazmak, sonraki oturumda başkasının çizimleriyle karışmak olurdu.
    if (etkinKimlik === null) return
    const { depo } = depoAl()
    if (depo === null) return
    const sonuc = kaydet(depo, etkinKimlik, symbol, cizimDurum.cizimler)
    // B5 (23.09.2026, bağımsız denetim): hata YALNIZCA bir sonraki başarılı
    // veri çekiminde temizleniyordu; kayıt/PNG hatası ekranda asılı kalıp
    // sorun çözüldükten sonra da kullanıcıyı yanıltıyordu. Başarılı kayıt
    // kendi hatasını kendisi temizler.
    setHata(sonuc.basarili ? '' : `${ARAYUZ_METINLERI.kayitHatasi}: ${sonuc.hata ?? ''}`)
  }, [bayrak, yuklenenSembol, symbol, etkinKimlik, cizimDurum.cizimler])

  // 6b) Gösterge seçimi değişince kaydet (ADR-5). Kapı ANAHTARIN TAMAMIDIR
  //     (kullanıcı+sembol): yükleme bu ad alanı için bitmeden yazılmaz.
  useEffect(() => {
    if (bayrak !== 'acik' || etkinKimlik === null) return
    if (yuklenenGostergeAnahtari !== gostergeAnahtari(etkinKimlik, symbol)) return
    const { depo } = depoAl()
    if (depo === null) return
    const sonuc = gostergeleriKaydet(depo, etkinKimlik, symbol, terminal.gostergeler, Date.now())
    setGostergeKayitHatasi(sonuc.basarili ? '' : `${ARAYUZ_METINLERI.gostergeKayitHatasi}: ${sonuc.hata ?? ''}`)
  }, [bayrak, etkinKimlik, symbol, yuklenenGostergeAnahtari, terminal.gostergeler])

  // 7) Çizim durumunu primitive'e ver (o da grafikten yeniden boyama ister).
  useEffect(() => {
    if (!grafikHazir) return
    primitiveRef.current?.durumAyarla(cizimDurum)
  }, [grafikHazir, cizimDurum])

  // 8) Grafik tıklaması: ya seçim (imleç) ya da nokta biriktirme (çizim aracı).
  useEffect(() => {
    if (!grafikHazir) return
    const grafik = grafikRef.current
    const seri = seriRef.current
    if (grafik === null || seri === null) return

    const tiklama = (param: MouseEventParams<Time>): void => {
      const konum = param.point
      if (konum === undefined) return

      if (terminal.arac === 'imlec') {
        // İsabet hesabı test edilmiş saf geometriden gelir; kütüphanenin
        // `hoveredInfo` alanına bağlanmak, burada doğrulanamayan bir
        // varsayım olurdu.
        const dnm = donusumYap(grafik, seri)
        const bulunan = enYakinCizim(cizimDurum.cizimler, konum.x, konum.y, dnm)
        cizimGonder({ tip: 'SEC', id: bulunan === null ? null : bulunan.cizim.id })
        // B5: imleç dalı `not`'u temizlemiyordu; önceki çizimden kalan
        // "nokta hesaplanamadı" notu ekranda asılı kalıyordu.
        setNot('')
        return
      }

      const fiyat = seri.coordinateToPrice(konum.y)
      const t_utc = zamanUtcMs(param.time ?? grafik.timeScale().coordinateToTime(konum.x))
      if (fiyat === null || t_utc === null) {
        setNot(ARAYUZ_METINLERI.noktaHesaplanamadi)
        return
      }
      const nokta: Nokta = { t_utc, fiyat }

      sayacRef.current += 1
      const olusturma_utc = Date.now()
      const kimlik: CizimKimligi = {
        // Aynı milisaniyede iki tıklama olabilir; sayaç kimliği benzersiz
        // kılar (yinelenen kimlik `cizim-model` reducer'ında EKLE'yi düşürür).
        id: `${olusturma_utc}-${sayacRef.current}`,
        olusturma_utc,
        stil: CIZIM_STILI,
      }
      if (terminal.arac === 'metin') {
        const girilen = window.prompt(ARAYUZ_METINLERI.metinIstemi)
        // Kullanıcı vazgeçtiyse hiçbir şey olmaz; boş metinli bir "metin
        // çizimi" ekranda görünmez bir nesne olurdu.
        if (girilen === null || girilen.trim() === '') return
        kimlik.metin = girilen.trim()
      }

      // Kararın TAMAMI saf modülde verilir; burada yalnızca sonucu uygularız.
      // Eylemleri yeniden kurmak yerine dönen durumu doğrudan yazmak, iki
      // tarafın ayrışmasını imkânsız kılar.
      const sonuc = tiklamaSonucu(terminal, nokta, kimlik)
      setTerminal(sonuc.yeniDurum)
      if (sonuc.tamamlananCizim !== undefined) {
        cizimGonder({ tip: 'EKLE', cizim: sonuc.tamamlananCizim })
      }
      setNot(sonuc.hata ?? '')
    }

    grafik.subscribeClick(tiklama)
    return () => grafik.unsubscribeClick(tiklama)
  }, [grafikHazir, terminal, cizimDurum.cizimler])

  // 9) Klavye: Delete = seçili çizimi silme, Escape = çizimi bırakma.
  useEffect(() => {
    if (bayrak !== 'acik') return
    const tus = (olay: KeyboardEvent): void => {
      const hedef = olay.target
      // Bir metin kutusuna yazarken Delete tuşu çizim silmemeli.
      if (hedef instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(hedef.tagName)) {
        return
      }
      if (olay.key === 'Escape') {
        terminalGonder({ tip: 'CIZIM_IPTAL' })
        cizimGonder({ tip: 'SEC', id: null })
        return
      }
      if (olay.key === 'Delete' || olay.key === 'Backspace') {
        if (cizimDurum.seciliId === null) return
        olay.preventDefault()
        cizimGonder({ tip: 'SIL', id: cizimDurum.seciliId })
      }
    }
    window.addEventListener('keydown', tus)
    return () => window.removeEventListener('keydown', tus)
  }, [bayrak, cizimDurum.seciliId])

  const pngIndir = (): void => {
    const grafik = grafikRef.current
    if (grafik === null) return
    try {
      // addTopLayer = TRUE olmadan primitive katmanı (yani kullanıcı
      // çizimleri) PNG'ye GİRMEZ — ölçülmüş kütüphane davranışı.
      const kanvas = grafik.takeScreenshot(true)
      const baglanti = document.createElement('a')
      baglanti.href = kanvas.toDataURL('image/png')
      baglanti.download = `${symbol}-${terminal.dilim}.png`
      baglanti.click()
      setHata('') // B5: başarılı indirme önceki PNG hatasını temizler
    } catch (sebep: unknown) {
      setHata(`${ARAYUZ_METINLERI.pngHatasi}: ${hataMetni(sebep)}`)
    }
  }

  // Bayrak kapalıysa bileşen TAMAMEN gizlenir (Hook'lardan SONRA: React
  // kuralı gereği erken dönüş, her render'da aynı sayıda Hook çalıştıktan
  // sonra gelmelidir — komşu BildirimMerkezi.tsx ile aynı desen).
  if (bayrak !== 'acik') return null

  const durumEtiketi = dilimEtiketi(
    terminal.dilim,
    dilimSonucu.turetildi,
    dilimSonucu.eksikSonKova,
  )
  const veriUyarisi = veriNotu(atlananHam, dilimSonucu.atlanan)
  const gosterilecekNot = [veriUyarisi, depoNotu, not].filter((m) => m !== null && m !== '').join(' · ')

  return (
    <section
      aria-label={ARAYUZ_METINLERI.baslik}
      style={{
        background: RENK.yuzey,
        border: `1px solid ${RENK.cizgi}`,
        borderRadius: 8,
        padding: 14,
        marginTop: 24,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ color: RENK.vurgu, fontWeight: 'bold', fontSize: 15 }}>
          {ARAYUZ_METINLERI.baslik}
        </span>
        <span style={{ color: RENK.metin, fontSize: 13 }}>{symbol}</span>
        <span style={{ color: RENK.ikincil, fontSize: 11 }}>{durumEtiketi}</span>
      </div>

      <div
        role="group"
        aria-label={ARAYUZ_METINLERI.zamanDilimi}
        style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 12 }}
      >
        {DILIM_SIRASI.map((dilim) => (
          <button
            key={dilim}
            type="button"
            aria-label={`${ARAYUZ_METINLERI.zamanDilimi}: ${DILIM_ETIKETLERI[dilim]}`}
            aria-pressed={terminal.dilim === dilim}
            onClick={() => terminalGonder({ tip: 'DILIM_SEC', dilim })}
            style={dugmeStili(terminal.dilim === dilim, false)}
          >
            {DILIM_ETIKETLERI[dilim]}
          </button>
        ))}
        {GUN_ICI_DILIMLER.map((etiket) => (
          <button
            key={etiket}
            type="button"
            disabled
            title={gunIciNeden()}
            aria-label={`${ARAYUZ_METINLERI.zamanDilimi}: ${etiket} — ${gunIciNeden()}`}
            style={dugmeStili(false, true)}
          >
            {etiket}
          </button>
        ))}
        <span style={{ color: RENK.soluk, fontSize: 11, alignSelf: 'center' }}>{gunIciNeden()}</span>
      </div>

      <div
        role="group"
        aria-label={ARAYUZ_METINLERI.araclar}
        style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}
      >
        {ARAC_SIRASI.map((arac) => (
          <button
            key={arac}
            type="button"
            aria-label={`${ARAYUZ_METINLERI.araclar}: ${ARAC_ETIKETLERI[arac]}`}
            aria-pressed={terminal.arac === arac}
            onClick={() => terminalGonder({ tip: 'ARAC_SEC', arac })}
            style={dugmeStili(terminal.arac === arac, false)}
          >
            {ARAC_ETIKETLERI[arac]}
          </button>
        ))}
      </div>

      <div
        role="group"
        aria-label={ARAYUZ_METINLERI.gostergeler}
        style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}
      >
        {tumGostergeKimlikleri().map((kimlik) => (
          <button
            key={kimlik}
            type="button"
            aria-label={`${ARAYUZ_METINLERI.gostergeler}: ${GOSTERGE_TANIMLARI[kimlik].etiket}`}
            aria-pressed={terminal.gostergeler.includes(kimlik)}
            onClick={() => terminalGonder({ tip: 'GOSTERGE_DEGISTIR', kimlik })}
            style={dugmeStili(terminal.gostergeler.includes(kimlik), false)}
          >
            {GOSTERGE_TANIMLARI[kimlik].etiket}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
        <button
          type="button"
          aria-label={ARAYUZ_METINLERI.geriAlAria}
          disabled={cizimDurum.geri.length === 0}
          onClick={() => cizimGonder({ tip: 'GERI_AL' })}
          style={dugmeStili(false, cizimDurum.geri.length === 0)}
        >
          {ARAYUZ_METINLERI.geriAl}
        </button>
        <button
          type="button"
          aria-label={ARAYUZ_METINLERI.yineleAria}
          disabled={cizimDurum.ileri.length === 0}
          onClick={() => cizimGonder({ tip: 'YINELE' })}
          style={dugmeStili(false, cizimDurum.ileri.length === 0)}
        >
          {ARAYUZ_METINLERI.yinele}
        </button>
        <button
          type="button"
          aria-label={ARAYUZ_METINLERI.temizleAria}
          disabled={cizimDurum.cizimler.length === 0}
          onClick={() => cizimGonder({ tip: 'TEMIZLE' })}
          style={dugmeStili(false, cizimDurum.cizimler.length === 0)}
        >
          {ARAYUZ_METINLERI.temizle}
        </button>
        <button
          type="button"
          aria-label={ARAYUZ_METINLERI.pngAria}
          onClick={pngIndir}
          style={dugmeStili(false, false)}
        >
          {ARAYUZ_METINLERI.png}
        </button>
        <span style={{ color: RENK.soluk, fontSize: 11, alignSelf: 'center' }}>
          {ARAYUZ_METINLERI.klavyeIpucu}
        </span>
      </div>

      {/* Hata ve uyarılar GÖRÜNÜR: sessizce boş bir grafik bırakılmaz (Y13). */}
      {(hata !== '' || gostergeKayitHatasi !== '') && (
        <div role="alert" style={{ color: RENK.hata, fontSize: 12, marginTop: 10 }}>
          {[hata, gostergeKayitHatasi].filter((m) => m !== '').join(' · ')}
        </div>
      )}
      {gosterilecekNot !== '' && (
        <div style={{ color: RENK.ikincil, fontSize: 11, marginTop: 6 }}>{gosterilecekNot}</div>
      )}
      {yukleniyor && (
        <div style={{ color: RENK.soluk, fontSize: 12, marginTop: 6 }}>
          {ARAYUZ_METINLERI.yukleniyor}
        </div>
      )}
      {!yukleniyor && hata === '' && dilimSonucu.barlar.length === 0 && (
        <div style={{ color: RENK.soluk, fontSize: 12, marginTop: 6 }}>
          {ARAYUZ_METINLERI.veriYok}
        </div>
      )}

      <div ref={kutuRef} style={{ marginTop: 10 }} />
    </section>
  )
}

/** Düğme görünümü; seçili ve devre dışı durumları ayırt edilebilir olmalı. */
function dugmeStili(secili: boolean, pasif: boolean): CSSProperties {
  return {
    background: secili ? RENK.vurgu : 'transparent',
    color: pasif ? RENK.soluk : secili ? '#0f172a' : RENK.metin,
    border: `1px solid ${secili ? RENK.vurgu : RENK.cizgi}`,
    borderRadius: 6,
    padding: '4px 10px',
    fontSize: 12,
    cursor: pasif ? 'not-allowed' : 'pointer',
    opacity: pasif ? 0.5 : 1,
  }
}
