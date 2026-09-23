// GÖSTERGE KATMANI — `gosterge-tanim.ts`'in ürettiği seri listesini
// lightweight-charts nesnelerine bağlayan İNCE kabuk.
//
// BU DOSYA TEST EDİLMEZ ve testi olmadığı için KARAR İÇERMEZ.
// Gerekçe: depoda jsdom yok, test koşucusu çıplak `node:test`; bir IChartApi
// örneklenemez, sahte nesne üretmek de kütüphanenin gerçek davranışını değil
// benim varsayımımı sınardı. Bu yüzden "hangi gösterge hangi seriyi, hangi
// panelde, hangi renkte üretir", "ısınma noktaları nasıl atlanır", "bilinmeyen
// kimliğe ne olur" sorularının TAMAMI `gosterge-tanim.ts`'tedir ve orada
// `tests/grafik/gosterge-tanim.test.ts` ile sınanır (28 test). Burada kalan
// yalnızca ekle / güncelle / kaldır mekaniğidir.
//
// KÜTÜPHANE İMZALARI (lightweight-charts 5.2.1, node_modules/lightweight-charts/dist/typings.d.ts):
//   satır 1640: addSeries<T extends SeriesType>(definition: SeriesDefinition<T>,
//               options?: SeriesPartialOptionsMap[T], paneIndex?: number): ISeriesApi<T, HorzScaleItem>
//   satır 1649: removeSeries(seriesApi: ISeriesApi<SeriesType, HorzScaleItem>): void
//   satır 1773: addPane(preserveEmptyPane?: boolean): IPaneApi<HorzScaleItem>
//   satır 1779: panes(): IPaneApi<HorzScaleItem>[]
//   satır 1785: removePane(index: number): void
//   satır 2037: IPaneApi.paneIndex(): number
import { HistogramSeries, LineSeries } from 'lightweight-charts'
import type { IChartApi, IPaneApi, ISeriesApi, SeriesType, Time } from 'lightweight-charts'
import type { CizilecekSeri, GostergeKimlik, GostergeNoktasi } from './gosterge-tanim'
import { gostergeSerileri, seriyiVeriyeCevir } from './gosterge-tanim'

/** Fiyat (mum) paneli. Grafik bileşeninin sahibi olduğu panel; buraya seri
 *  EKLERİZ ama bu panelin kendisine ya da içindeki başka serilere dokunmayız. */
const ANA_PANEL_INDEKSI = 0

/**
 * Eklenen tek bir seri.
 *
 * `veriYaz`, seri yaratılırken KAPANIŞ olarak saklanır. Nedeni tip güvenliği:
 * `ISeriesApi<'Line'>` ve `ISeriesApi<'Histogram'>` farklı `setData` imzalarına
 * sahiptir ve ikisinin birleşimi üzerinde `setData` çağrılamaz. Kapanışı
 * yaratıldığı yerde — tip henüz daralmışken — kurmak, tip kaçışı ya da zorlama
 * kullanmadan (Y13) çağrıyı doğru imzaya bağlar.
 */
type EklenenSeri = {
  api: ISeriesApi<SeriesType, Time>
  veriYaz(noktalar: GostergeNoktasi[]): void
}

export class GostergeKatmani {
  private readonly grafik: IChartApi

  /**
   * Bizim eklediğimiz seriler; anahtar `CizilecekSeri.ad`.
   * SINIR: bu haritada yalnızca KENDİ serilerimiz vardır. Mum serisi, olay
   * marker'ları ve başka katmanların serileri buraya hiç girmez, dolayısıyla
   * `temizle()` bile onlara dokunamaz.
   */
  private readonly seriler = new Map<string, EklenenSeri>()

  /**
   * Alt panel göstergesi başına bir panel. İNDEKS DEĞİL, panel NESNESİ saklanır:
   * bir panel kaldırıldığında sonrakilerin indeksi kayar, saklanmış bir sayı
   * sessizce yanlış paneli gösterirdi. `paneIndex()` ise her seferinde güncel
   * değeri okur (typings satır 2037).
   */
  private readonly altPaneller = new Map<GostergeKimlik, IPaneApi<Time>>()

  constructor(grafik: IChartApi) {
    this.grafik = grafik
  }

  /**
   * Seçili göstergeleri grafiğe yansıtır: eksikleri ekler, var olanların
   * verisini tazeler, artık istenmeyenleri kaldırır.
   *
   * Aynı girdiyle tekrar çağrılması güvenlidir (idempotent); React'in her
   * render'ında çağrılabilir.
   */
  uygula(kimlikler: readonly string[], zamanlar: string[], kapanislar: number[]): void {
    const istenen = gostergeSerileri(kimlikler, kapanislar)
    const istenenAdlar = new Set(istenen.map((seri) => seri.ad))
    const istenenAltKimlikler = new Set(
      istenen.filter((seri) => seri.panel === 'alt').map((seri) => seri.kimlik),
    )

    // 1) Önce kaldır. Panelin boşalması, panelin kaldırılmasından ÖNCE olmalı;
    //    tersi sırada dolu bir panel kaldırılır ve içindeki seriler sessizce
    //    kaybolurdu (haritada ölü referans kalırdı).
    for (const [ad, kayit] of this.seriler) {
      if (istenenAdlar.has(ad)) continue
      this.grafik.removeSeries(kayit.api)
      this.seriler.delete(ad)
    }

    // 2) Artık göstergesi kalmayan alt panelleri kaldır.
    for (const [kimlik, panel] of this.altPaneller) {
      if (istenenAltKimlikler.has(kimlik)) continue
      this.grafik.removePane(panel.paneIndex())
      this.altPaneller.delete(kimlik)
    }

    // 3) Ekle / güncelle.
    for (const seri of istenen) {
      const noktalar = seriyiVeriyeCevir(zamanlar, seri.degerler)
      let kayit = this.seriler.get(seri.ad)
      if (!kayit) {
        kayit = this.seriYarat(seri)
        this.seriler.set(seri.ad, kayit)
      }
      kayit.veriYaz(noktalar)
    }
  }

  /**
   * Katmanın eklediği HER ŞEYİ geri alır. React `useEffect` temizliğinde
   * çağrılır.
   *
   * ÇAĞRI SIRASI SÖZLEŞMESİ: `chart.remove()`'dan ÖNCE çağrılmalıdır. Grafik
   * yok edildikten sonra seri/panel kaldırmak kütüphanede hata fırlatır; bu
   * durumu burada yakalayıp yutmak, gerçek bir yaşam döngüsü hatasını
   * görünmez kılardı.
   */
  temizle(): void {
    for (const kayit of this.seriler.values()) {
      this.grafik.removeSeries(kayit.api)
    }
    this.seriler.clear()
    for (const panel of this.altPaneller.values()) {
      this.grafik.removePane(panel.paneIndex())
    }
    this.altPaneller.clear()
  }

  /** Göstergenin paneli; alt panel göstergesi için yoksa açılır. */
  private panelIndeksi(seri: CizilecekSeri): number {
    if (seri.panel === 'ana') return ANA_PANEL_INDEKSI
    const mevcut = this.altPaneller.get(seri.kimlik)
    if (mevcut) return mevcut.paneIndex()
    // preserveEmptyPane = true: panelin ömrü YALNIZCA bize ait olsun. Varsayılan
    // (false) davranışta, içindeki son seri kaldırıldığında kütüphane paneli
    // kendiliğinden düşürebilir; o anda elimizdeki panel referansı ölür ve
    // `removePane` yanlış indeksi hedefler. Paneli biz açıyor, biz kapatıyoruz.
    const panel = this.grafik.addPane(true)
    this.altPaneller.set(seri.kimlik, panel)
    return panel.paneIndex()
  }

  private seriYarat(seri: CizilecekSeri): EklenenSeri {
    const panelIndeksi = this.panelIndeksi(seri)
    if (seri.cizim === 'histogram') {
      const api = this.grafik.addSeries(
        HistogramSeries,
        {
          color: seri.renk,
          base: 0,
          title: seri.ad,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        panelIndeksi,
      )
      return { api, veriYaz: (noktalar) => api.setData(noktalar) }
    }
    const api = this.grafik.addSeries(
      LineSeries,
      {
        color: seri.renk,
        lineWidth: 2,
        title: seri.ad,
        // Gösterge çizgisi için fiyat çizgisi ve son değer etiketi kapalı:
        // fiyat ekseni mum serisinin etiketlerine ait, göstergeler onu
        // kalabalıklaştırmamalı.
        priceLineVisible: false,
        lastValueVisible: false,
      },
      panelIndeksi,
    )
    return { api, veriYaz: (noktalar) => api.setData(noktalar) }
  }
}
