// ============================================================================
// ÇİZİM PRIMITIVE'İ — kullanıcı çizimlerinin lightweight-charts katmanı
// ============================================================================
//
// BU DOSYA DOĞRUDAN TEST EDİLMEZ — BİLEREK.
// Deponun test koşucusu çıplak `node:test`'tir; jsdom ve canvas YOKTUR, DOM
// testi kurulmayacaktır. Bu yüzden buradaki her satır ya kütüphane çağrısı ya
// da canvas boyamasıdır: karar, ölçü ve etiket üreten TÜM hesap
// `cizim-geometri.ts`'e taşınmıştır ve orada 43 testle doğrulanır. Bu dosyaya
// bir "if" eklemek istediğinizde, o "if" büyük olasılıkla geometriye aittir.
//
// ÖLÇÜLMÜŞ API (tahmin YOK). Satır numaraları:
//   node_modules/lightweight-charts/dist/typings.d.ts (sürüm 5.2.1)
//     4774  ISeriesPrimitive<HorzScaleItem> = ISeriesPrimitiveBase<SeriesAttachedParameter<...>>
//     2697  ISeriesPrimitiveBase.updateAllViews?(): void
//     2724  ISeriesPrimitiveBase.paneViews?(): readonly IPrimitivePaneView[]
//     2762  ISeriesPrimitiveBase.attached?(param): void
//     2768  ISeriesPrimitiveBase.detached?(): void
//     2780  ISeriesPrimitiveBase.hitTest?(x, y): PrimitiveHoveredItem | null
//     2314  IPrimitivePaneView            (2320 zOrder?(), 2326 renderer())
//     2292  IPrimitivePaneRenderer        (2300 draw(target, utils?))
//     3868  SeriesAttachedParameter       (3872 chart, 3876 series, 3880 requestUpdate)
//     2357  ISeriesApi.priceToCoordinate(price): Coordinate | null
//     1747  IChartApiBase.timeScale(): ITimeScaleApi<HorzScaleItem>
//     2946  ITimeScaleApi.timeToCoordinate(time): Coordinate | null
//     4889  PrimitivePaneViewZOrder = "bottom" | "normal" | "top"
//     4987  Time = UTCTimestamp | BusinessDay | string
//     3819  PrimitiveHoveredItem (3824 distance?, 3838 hitTestPriority?, 3843 cursorStyle?,
//                                 3847 externalId, 3851 zOrder)
//   node_modules/fancy-canvas/canvas-rendering-target.d.ts
//     13-19 BitmapCoordinatesRenderingScope (context, bitmapSize, horizontalPixelRatio,
//                                            verticalPixelRatio)
//     29    CanvasRenderingTarget2D.useBitmapCoordinateSpace<T>(f): T
//
// NEDEN `CanvasRenderingTarget2D` İTHAL EDİLMİYOR: bu tip lightweight-charts
// typings'inde yalnızca İÇERİ alınır (satır 3), DIŞA açılmaz; doğrudan
// 'fancy-canvas'tan almak ise package.json'da bulunmayan dolaylı bir bağımlılığa
// dayanmak olurdu. Bunun yerine tip, `IPrimitivePaneRenderer.draw`'ın ilk
// parametresinden TÜRETİLİR — kütüphane sürümü değişirse tip de kendiliğinden
// değişir, elle yazılmış bir kopya eskimez.
//
// NEDEN `updateAllViews()` İÇİNDE HESAPLANIYOR: kütüphanenin çizim yolu
// ölçüldü — PaneWidget._internal_paint(), Cursor seviyesinin üzerindeki HER
// geçersizleştirmede _internal_recalculatePriceScales()'i, o da pano
// primitive'lerinin updateAllViews()'unu çağırıyor
// (lightweight-charts.development.mjs, satır 9876 -> 5454 -> 3191). Yani
// panonun boyandığı her karede bu metot önce çalışır; koordinatları burada
// bir kez hesaplayıp renderer'da yalnızca boyamak bayat koordinat riski
// yaratmaz.
//
// NEDEN İŞ GÜNÜ STRINGİ (UTCTimestamp değil): grafiğin mum serisi
// "YYYY-MM-DD" biçiminde beslenir (components/PriceChart.tsx) ve
// timeToCoordinate, zamanı `timeToIndex(time, false)` ile TAM eşleşme arayarak
// çözer (development.mjs satır 13004-13010). Seri hangi biçimle beslendiyse
// sorgunun da o biçimde olması gerekir. Dönüşüm koyfin-zaman.ts'in
// yardımcısıyla yapılır; depo kuralı gereği tarih biçimlendirmesi başka hiçbir
// dosyada elle yazılmaz.

import type {
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesPrimitive,
  PrimitiveHoveredItem,
  PrimitivePaneViewZOrder,
  SeriesAttachedParameter,
  SeriesType,
  Time,
} from 'lightweight-charts'
import { utcMsToIsGunuString } from '../koyfin-zaman'
import type { Durum } from './cizim-model'
import { bosDurum } from './cizim-model'
import type { Donusum, EkranNoktasi, Gorunum } from './cizim-geometri'
import { HIT_ESIK_PX, cizimGorunumu, enYakinCizim, tutamacNoktalari } from './cizim-geometri'

/** Boyama hedefi — kütüphanenin kendi imzasından türetilir (bkz. dosya başlığı). */
type BoyamaHedefi = Parameters<IPrimitivePaneRenderer['draw']>[0]

/** Bir karede boyanacak tek bir çizim: artık tamamı pikseldir, veri değil. */
type CizilecekOge = {
  gorunum: Gorunum
  renk: string
  kalinlik: number
  tutamaclar: EkranNoktasi[]
}

/** Seçim tutamacının kenar uzunluğu (CSS pikseli). */
const TUTAMAC_PX = 6
/** Etiket yazı boyu (CSS pikseli). */
const YAZI_PX = 11
/** Etiketin çizgiden kaçırılma payı (CSS pikseli) — çizginin üstüne binmesin. */
const ETIKET_PAYI = 6
/** Dikdörtgen dolgusunun saydamlığı: altındaki mumlar okunur kalmalı. */
const DOLGU_ALFA = 0.12

export class CizimPrimitive implements ISeriesPrimitive<Time> {
  /**
   * Durum DIŞARIDAN gelir; bu sınıf onu ne üretir ne değiştirir. Çizim
   * mantığının tek sahibi `cizim-model.ts` reducer'ıdır (bkz. o dosyanın
   * "NEDEN SAF BİR REDUCER" başlığı).
   */
  private durum: Durum = bosDurum()

  /**
   * `attached` ile gelen bağlam. Kurucuya getirici fonksiyon geçmek yerine bu
   * resmi yaşam döngüsü kancası kullanılır: `requestUpdate` (satır 3880)
   * YALNIZCA buradan gelir; onsuz durum değişince grafik yeniden boyanmaz ve
   * kullanıcı çizimini bir sonraki fare hareketine kadar göremezdi.
   */
  private baglam: SeriesAttachedParameter<Time, SeriesType> | null = null

  /** `updateAllViews` içinde hesaplanıp renderer'da boyanan kare verisi. */
  private ogeler: CizilecekOge[] = []

  /**
   * Pano görünümü TEK ve DEĞİŞMEZ bir dizide tutulur.
   * NEDEN: kütüphane, görünüm kümesini dizi REFERANSINA göre önbelleğe alır
   * (typings.d.ts satır 2721-2722 notu); her çağrıda yeni dizi döndürmek
   * önbelleği gereksizce boşa düşürürdü.
   */
  private readonly panoGorunumleri: readonly IPrimitivePaneView[]

  constructor() {
    const gorunum: IPrimitivePaneView = {
      // Çizimler mumların ÜSTÜNDE durur: kullanıcı onları mum gövdesinin
      // arkasında kaybetmemeli.
      zOrder: (): PrimitivePaneViewZOrder => 'top',
      renderer: (): IPrimitivePaneRenderer => ({
        draw: (hedef: BoyamaHedefi): void => this.boya(hedef),
      }),
    }
    this.panoGorunumleri = [gorunum]
  }

  /** Kütüphane kancası: seri/grafik bağlamını alır (typings 2762). */
  attached(param: SeriesAttachedParameter<Time, SeriesType>): void {
    this.baglam = param
  }

  /** Kütüphane kancası: bağlam koparıldı (typings 2768). Tutulan referanslar
   *  bırakılır; kaldırılmış bir grafiğe ait koordinat hesabı yapılmaz. */
  detached(): void {
    this.baglam = null
    this.ogeler = []
  }

  /**
   * Dışarıdan durum güncellemesi. Yeni durumu saklar ve grafikten yeniden
   * boyama ister; boyama sırasında `updateAllViews` çalışıp koordinatlar
   * yeniden hesaplanır.
   */
  durumAyarla(durum: Durum): void {
    this.durum = durum
    this.baglam?.requestUpdate()
  }

  /** Kütüphane kancası: her boyama karesinden önce çağrılır (typings 2697). */
  updateAllViews(): void {
    this.ogeler = this.ogeleriHesapla()
  }

  /** Kütüphane kancası: pano görünümleri (typings 2724). */
  paneViews(): readonly IPrimitivePaneView[] {
    return this.panoGorunumleri
  }

  /**
   * Kütüphane kancası: imleç isabeti (typings 2780). Koordinatlar CSS
   * pikselidir — `priceToCoordinate` ile aynı birim, dolayısıyla geometriye
   * doğrudan verilir.
   */
  hitTest(x: number, y: number): PrimitiveHoveredItem | null {
    const dnm = this.donusum()
    if (dnm === null) return null
    const bulunan = enYakinCizim(this.durum.cizimler, x, y, dnm, HIT_ESIK_PX)
    if (bulunan === null) return null
    return {
      externalId: bulunan.cizim.id,
      zOrder: 'top',
      cursorStyle: 'pointer',
      distance: bulunan.uzaklik,
      // 1 = çizgi biçimli isabet (typings 3829-3832'deki öneri ölçeği).
      hitTestPriority: 1,
    }
  }

  /**
   * Grafik -> ekran dönüşümü. Bağlam yoksa (henüz attach edilmedi / detach
   * edildi) dönüşüm de yoktur; sahte bir dönüşüm üretmek çizimleri ekranın
   * sol üstüne yığardı (Y3).
   */
  private donusum(): Donusum | null {
    const baglam = this.baglam
    if (baglam === null) return null
    const seri = baglam.series
    const zamanOlcegi = baglam.chart.timeScale()
    return {
      zamanX: (t_utc: number): number | null => zamanOlcegi.timeToCoordinate(utcMsToIsGunuString(t_utc)),
      fiyatY: (fiyat: number): number | null => seri.priceToCoordinate(fiyat),
    }
  }

  /** Durumu, o anki ölçeklerle piksel uzayına indirger. */
  private ogeleriHesapla(): CizilecekOge[] {
    const dnm = this.donusum()
    if (dnm === null) return []
    const ogeler: CizilecekOge[] = []
    for (const cizim of this.durum.cizimler) {
      const gorunum = cizimGorunumu(cizim, dnm)
      // Ekrana düşmeyen çizim ATLANIR; yaklaşık bir konuma çizilmez (Y3).
      if (gorunum === null) continue
      const secili = cizim.id === this.durum.seciliId
      ogeler.push({
        gorunum,
        renk: cizim.stil.renk,
        kalinlik: cizim.stil.kalinlik,
        tutamaclar: secili ? tutamacNoktalari(cizim, dnm) : [],
      })
    }
    return ogeler
  }

  /**
   * Canvas boyaması. Bitmap uzayında çalışılır: geometriden gelen değerler CSS
   * pikselidir, cihaz piksel oranıyla çarpılarak keskin (yarım piksele
   * bulaşmayan) çizgi elde edilir.
   */
  private boya(hedef: BoyamaHedefi): void {
    const ogeler = this.ogeler
    if (ogeler.length === 0) return
    hedef.useBitmapCoordinateSpace((kapsam) => {
      const ctx = kapsam.context
      const gx = kapsam.horizontalPixelRatio
      const gy = kapsam.verticalPixelRatio
      ctx.save()
      for (const oge of ogeler) {
        ctx.strokeStyle = oge.renk
        ctx.fillStyle = oge.renk
        ctx.lineWidth = Math.max(1, oge.kalinlik * gy)
        ctx.font = `${Math.round(YAZI_PX * gy)}px sans-serif`
        ctx.textBaseline = 'bottom'
        this.gorunumBoya(ctx, oge.gorunum, gx, gy, kapsam.bitmapSize.width, kapsam.bitmapSize.height)
        for (const tutamac of oge.tutamaclar) {
          ctx.fillRect(
            tutamac.x * gx - (TUTAMAC_PX / 2) * gx,
            tutamac.y * gy - (TUTAMAC_PX / 2) * gy,
            TUTAMAC_PX * gx,
            TUTAMAC_PX * gy,
          )
        }
      }
      ctx.restore()
    })
  }

  private gorunumBoya(
    ctx: CanvasRenderingContext2D,
    gorunum: Gorunum,
    gx: number,
    gy: number,
    en: number,
    boy: number,
  ): void {
    switch (gorunum.tip) {
      case 'segment': {
        this.cizgiBoya(ctx, gorunum.a.x * gx, gorunum.a.y * gy, gorunum.b.x * gx, gorunum.b.y * gy)
        if (gorunum.etiket !== null) {
          // Etiket parçanın ortasının biraz üstünde durur; çizgiyi örtmez.
          const ortaX = ((gorunum.a.x + gorunum.b.x) / 2) * gx
          const ortaY = ((gorunum.a.y + gorunum.b.y) / 2) * gy
          ctx.fillText(gorunum.etiket, ortaX + ETIKET_PAYI * gx, ortaY - ETIKET_PAYI * gy)
        }
        return
      }

      case 'yatay': {
        // Panonun TAM genişliği: yatay çizgi bir fiyat seviyesidir, iki nokta
        // arasındaki bir parça değil.
        this.cizgiBoya(ctx, 0, gorunum.y * gy, en, gorunum.y * gy)
        return
      }

      case 'dikey': {
        this.cizgiBoya(ctx, gorunum.x * gx, 0, gorunum.x * gx, boy)
        return
      }

      case 'dikdortgen': {
        const solX = Math.min(gorunum.a.x, gorunum.b.x) * gx
        const ustY = Math.min(gorunum.a.y, gorunum.b.y) * gy
        const genislik = Math.abs(gorunum.b.x - gorunum.a.x) * gx
        const yukseklik = Math.abs(gorunum.b.y - gorunum.a.y) * gy
        // Dolgu, rengi ayrıştırmak yerine globalAlpha ile saydamlaştırılır:
        // `stil.renk` her biçimde ("#rgb", "#rrggbb", isim) gelebilir ve elle
        // ayrıştırmak sessizce yanlış renk üretebilirdi.
        const oncekiAlfa = ctx.globalAlpha
        ctx.globalAlpha = DOLGU_ALFA
        ctx.fillRect(solX, ustY, genislik, yukseklik)
        ctx.globalAlpha = oncekiAlfa
        ctx.strokeRect(solX, ustY, genislik, yukseklik)
        return
      }

      case 'fib': {
        for (const cizgi of gorunum.cizgiler) {
          this.cizgiBoya(ctx, 0, cizgi.y * gy, en, cizgi.y * gy)
          // Etiket sol kenarda: seviyeler yatay olduğu için sağa kaydırmak
          // onları grafiğin kaydırılan kısmında görünmez kılardı.
          ctx.fillText(cizgi.etiket, ETIKET_PAYI * gx, cizgi.y * gy - 2 * gy)
        }
        return
      }

      case 'metin': {
        const x = gorunum.nokta.x * gx
        const y = gorunum.nokta.y * gy
        // Tutturma noktası küçük bir kare ile işaretlenir: metin taşınınca
        // hangi noktaya bağlı olduğu görünür kalsın.
        ctx.fillRect(x - gx, y - gy, 2 * gx, 2 * gy)
        ctx.fillText(gorunum.metin, x + ETIKET_PAYI * gx, y - ETIKET_PAYI * gy)
        return
      }

      default: {
        // Geometriye yeni bir görünüm tipi eklenip burada karşılıksız kalırsa
        // DERLEME hatası verir; ekranda sessizce eksik çizim olmaz.
        const eksikTip: never = gorunum
        void eksikTip
        return
      }
    }
  }

  private cizgiBoya(ctx: CanvasRenderingContext2D, ax: number, ay: number, bx: number, by: number): void {
    ctx.beginPath()
    ctx.moveTo(ax, ay)
    ctx.lineTo(bx, by)
    ctx.stroke()
  }
}
