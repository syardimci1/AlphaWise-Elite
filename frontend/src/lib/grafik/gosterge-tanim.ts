// GÖSTERGE TANIM KATMANI — hangi göstergenin hangi seriyi, hangi panelde,
// hangi renkte ve hangi çizim biçiminde ürettiğinin TEK doğruluk kaynağı.
//
// NEDEN AYRI BİR DOSYA: bu depoda DOM testi yok (jsdom kurulu değil), grafik
// kütüphanesi de saf bir test koşucusunda örneklenemez. Bu yüzden "ne çizilecek"
// KARARI ile "nasıl çizilecek" İŞİ bilerek ayrıldı. Karar burada — saf, DOM'suz,
// kütüphanesiz — ve testlerin tamamı buraya bakar. Kütüphaneye dokunan tek
// dosya `gosterge-katmani.ts`'tir ve orada hiçbir karar yoktur.
//
// SÖZLEŞME:
//  - SAFLIK: girdi dizileri MUTASYONA UĞRAMAZ, rastgelelik/zaman yoktur.
//  - Y3 (sahte veri yasağı): ısınma penceresindeki hesaplanamayan noktalar
//    `null` gelir ve grafiğe AKTARILMAZ; yerlerine sıfır/enterpolasyon
//    UYDURULMAZ. Eksik nokta, eksik nokta olarak kalır.
//  - Y8 (hukuki dil): buradaki etiketler ve seri adları arayüzde görünür,
//    bu yüzden tamamı TARİFSELDİR — "SMA 20", "RSI 14" gibi. Yorum, tavsiye,
//    al/sat çağrısı, hedef fiyat ya da "fırsat" dili YOKTUR ve eklenemez;
//    `gosterge-tanim.test.ts` bunu yasaklı kalıp listesiyle sınar.
import { sma, ema, bollinger, rsi, macd } from './gostergeler'

export type GostergeKimlik = 'sma20' | 'sma50' | 'ema20' | 'bollinger20' | 'rsi14' | 'macd'

/** Gösterge ana fiyat paneline mi, kendi alt paneline mi çizilir. */
export type GostergePanel = 'ana' | 'alt'

/** Serinin grafikteki çizim biçimi. Yalnızca MACD histogramı çubuk ister. */
export type GostergeCizimTipi = 'cizgi' | 'histogram'

/** `hesapla` çıktısı: bir göstergenin ürettiği tek bir sayı serisi. */
export type HesaplananSeri = {
  ad: string
  seri: (number | null)[]
}

export type GostergeTanimi = {
  kimlik: GostergeKimlik
  /** Arayüzde kullanıcıya gösterilen ad. Yalnızca tarifsel olabilir (Y8). */
  etiket: string
  panel: GostergePanel
  /**
   * `hesapla()` çıktısıyla İNDEKS İNDEKS eşleşen renk listesi.
   * Uzunlukların eşitliği bir değişmezdir ve testle sınanır; eşit olmazsa
   * bir seri renksiz kalırdı ve kütüphane kendi varsayılan rengini basardı —
   * yani kullanıcı hangi çizginin hangi gösterge olduğunu ayırt edemezdi.
   */
  renkler: readonly string[]
  /**
   * İsteğe bağlı çizim biçimi listesi; verilmezse tüm seriler 'cizgi' kabul
   * edilir. Yalnızca MACD'de gerekiyor, bu yüzden her tanıma zorunlu bir alan
   * olarak eklenmedi.
   */
  cizimler?: readonly GostergeCizimTipi[]
  hesapla(kapanislar: number[]): HesaplananSeri[]
}

/** Çizilmeye hazır tek bir seri: ne, nerede, hangi renkte, hangi biçimde. */
export type CizilecekSeri = {
  /**
   * Seriyi üreten göstergenin kimliği.
   *
   * NEDEN TAŞINIYOR: alt panel göstergeleri PANEL BAŞINA gruplanır. RSI 0-100
   * arasında, MACD ise sıfır çevresinde (birkaç birim) salınır; ikisi aynı
   * fiyat ölçeğini paylaşırsa MACD ekranın dibinde düz bir çizgiye çöker.
   * Katman bu alana bakarak her alt panel göstergesine KENDİ panelini açar.
   */
  kimlik: GostergeKimlik
  /**
   * Seri adı. Arayüzde etiket olmasının yanında `gosterge-katmani.ts`'te
   * Map ANAHTARI olarak da kullanılır: aynı ad iki farklı seriye verilirse
   * biri diğerinin üstüne yazılır ve grafikten sessizce kaybolur. Bu yüzden
   * adların TÜM göstergeler genelinde benzersizliği testle sınanır.
   */
  ad: string
  renk: string
  panel: GostergePanel
  cizim: GostergeCizimTipi
  degerler: (number | null)[]
}

/**
 * lightweight-charts'ın `LineData`/`HistogramData` biçimi.
 *
 * Alan adları İngilizce (`time`, `value`) çünkü bunlar bizim değil,
 * kütüphanenin sözleşmesidir; Türkçeleştirilirse kütüphane veriyi okuyamaz.
 * Zaman tipi `string` ("YYYY-MM-DD") — grafik bileşeni barları bu biçimde
 * veriyor (bkz. koyfin-zaman.ts / utcMsToIsGunuString).
 */
export type GostergeNoktasi = {
  time: string
  value: number
}

const SMA20_RENK = '#2962ff'
const SMA50_RENK = '#ff6d00'
const EMA20_RENK = '#00897b'
const BOLLINGER_BANT_RENK = '#7e57c2'
const BOLLINGER_ORTA_RENK = '#b39ddb'
const RSI_RENK = '#ab47bc'
const MACD_RENK = '#2962ff'
const MACD_SINYAL_RENK = '#ff6d00'
const MACD_HISTOGRAM_RENK = '#90a4ae'

/**
 * Tanım tablosu. Parametreler (20, 50, 14, 12/26/9) etiketlerin İÇİNE
 * yazılmıştır: kullanıcı ayar panelini açmadan hangi pencerenin çizildiğini
 * görebilmelidir, aksi halde iki farklı SMA ayırt edilemez.
 *
 * MACD'nin ikinci serisi TA literatüründe "sinyal çizgisi" adını taşır ve
 * MACD çizgisinin 9 periyotluk EMA'sıdır; buradaki "Sinyal" sözcüğü bir
 * işlem çağrısı değil, o bileşenin adıdır. Yanlış okunmaması için periyot
 * etikete açıkça yazıldı.
 */
export const GOSTERGE_TANIMLARI: Readonly<Record<GostergeKimlik, GostergeTanimi>> = {
  sma20: {
    kimlik: 'sma20',
    etiket: 'SMA 20',
    panel: 'ana',
    renkler: [SMA20_RENK],
    hesapla: (kapanislar) => [{ ad: 'SMA 20', seri: sma(kapanislar, 20) }],
  },
  sma50: {
    kimlik: 'sma50',
    etiket: 'SMA 50',
    panel: 'ana',
    renkler: [SMA50_RENK],
    hesapla: (kapanislar) => [{ ad: 'SMA 50', seri: sma(kapanislar, 50) }],
  },
  ema20: {
    kimlik: 'ema20',
    etiket: 'EMA 20',
    panel: 'ana',
    renkler: [EMA20_RENK],
    hesapla: (kapanislar) => [{ ad: 'EMA 20', seri: ema(kapanislar, 20) }],
  },
  bollinger20: {
    kimlik: 'bollinger20',
    etiket: 'Bollinger (20, 2)',
    panel: 'ana',
    renkler: [BOLLINGER_BANT_RENK, BOLLINGER_ORTA_RENK, BOLLINGER_BANT_RENK],
    hesapla: (kapanislar) => {
      const bantlar = bollinger(kapanislar, 20, 2)
      // Sıra üst -> orta -> alt: `renkler` ile indeks indeks eşleşir ve iki
      // bant aynı rengi, orta çizgi ayrı bir tonu alır.
      return [
        { ad: 'Bollinger Üst (20, 2)', seri: bantlar.ust },
        { ad: 'Bollinger Orta (20, 2)', seri: bantlar.orta },
        { ad: 'Bollinger Alt (20, 2)', seri: bantlar.alt },
      ]
    },
  },
  rsi14: {
    kimlik: 'rsi14',
    etiket: 'RSI 14',
    // Ölçeği 0-100, fiyatla aynı eksene sığmaz; kendi panelini ister.
    panel: 'alt',
    renkler: [RSI_RENK],
    hesapla: (kapanislar) => [{ ad: 'RSI 14', seri: rsi(kapanislar, 14) }],
  },
  macd: {
    kimlik: 'macd',
    etiket: 'MACD (12, 26, 9)',
    // Sıfır çevresinde salınır; fiyat ekseninde görünmez kalırdı.
    panel: 'alt',
    renkler: [MACD_RENK, MACD_SINYAL_RENK, MACD_HISTOGRAM_RENK],
    cizimler: ['cizgi', 'cizgi', 'histogram'],
    hesapla: (kapanislar) => {
      const sonuc = macd(kapanislar, 12, 26, 9)
      return [
        { ad: 'MACD (12, 26, 9)', seri: sonuc.macd },
        { ad: 'MACD Sinyal (9)', seri: sonuc.sinyal },
        { ad: 'MACD Histogram', seri: sonuc.histogram },
      ]
    },
  },
}

const KIMLIKLER: readonly GostergeKimlik[] = Object.keys(GOSTERGE_TANIMLARI) as GostergeKimlik[]

/**
 * Bir dizgenin bilinen bir gösterge kimliği olup olmadığını söyler.
 *
 * NEDEN DIŞA AÇIK: seçili gösterge listesi localStorage'dan / adres
 * satırından gelir, yani sınırda tipi `string`'tir. Çağıran taraf bilinmeyen
 * bir kimliği FARK EDEBİLSİN diye ayrı bir kapı bırakıldı; `gostergeSerileri`
 * bilinmeyeni sessizce atlar, bu kapı ise onu görünür kılar.
 */
export function gostergeKimlikMi(deger: string): deger is GostergeKimlik {
  return Object.prototype.hasOwnProperty.call(GOSTERGE_TANIMLARI, deger)
}

/** Arayüzün gösterge listesini kurabilmesi için tanımlı kimliklerin sırası. */
export function tumGostergeKimlikleri(): GostergeKimlik[] {
  return [...KIMLIKLER]
}

/**
 * Seçili kimlikler için çizilecek serilerin düz listesi.
 *
 * Parametre tipi bilerek `readonly string[]`: kimlikler kalıcı depodan gelir
 * ve eski bir sürümde var olup artık bulunmayan bir kimlik taşıyabilir.
 *
 * BİLİNMEYEN KİMLİK: atlanır. Bu, depodaki "sessizce yutma" yasağının bir
 * istisnası DEĞİL — atlanan şey ölçüm verisi değil, bir arayüz anahtarıdır;
 * karşılığı olmayan bir gösterge çizilemez ve yerine bir şey UYDURULAMAZ.
 * Çağıran taraf farkı görmek isterse `gostergeKimlikMi` ile önceden eleyebilir.
 *
 * TEKRAR EDEN KİMLİK: bir kez üretilir. Aksi halde aynı `ad`'a sahip iki seri
 * doğardı ve katmanın Map anahtarı çakışırdı.
 */
export function gostergeSerileri(
  kimlikler: readonly string[],
  kapanislar: number[],
): CizilecekSeri[] {
  const sonuc: CizilecekSeri[] = []
  const gorulen = new Set<string>()
  for (const kimlik of kimlikler) {
    if (!gostergeKimlikMi(kimlik)) continue
    if (gorulen.has(kimlik)) continue
    gorulen.add(kimlik)
    const tanim = GOSTERGE_TANIMLARI[kimlik]
    const hesaplanan = tanim.hesapla(kapanislar)
    for (let i = 0; i < hesaplanan.length; i++) {
      sonuc.push({
        kimlik,
        ad: hesaplanan[i].ad,
        renk: tanim.renkler[i],
        panel: tanim.panel,
        cizim: tanim.cizimler ? tanim.cizimler[i] : 'cizgi',
        degerler: hesaplanan[i].seri,
      })
    }
  }
  return sonuc
}

/**
 * (number|null)[] serisini lightweight-charts'ın kabul ettiği nokta dizisine
 * çevirir.
 *
 * NULL NOKTA ATLANIR — whitespace kaydı bile yazılmaz. Gerekçe: ısınma
 * penceresi "o gün gösterge yoktu" demektir, "değeri boştu" değil; kütüphane
 * eksik noktayı zaten çizgide boşluk olarak gösterir. Sıfır ya da komşudan
 * taşınmış bir değer yazmak Y3 ihlali olurdu.
 *
 * SONLU OLMAYAN DEĞER de atlanır. `gostergeler.ts` NaN/Infinity'yi zaten
 * kapıda tutuyor; buradaki ikinci kapı, kütüphaneye NaN geçtiğinde ortaya
 * çıkan sessiz bozuk çizimi imkânsız kılmak için var.
 *
 * UZUNLUK UYUŞMAZLIĞI: yalnızca ortak ön-ek çevrilir. Zaman ve değer dizileri
 * indeksle eşleştiği için fazlalık kuyruğun hangi tarihe ait olduğu bilinemez;
 * tahmin yürütmek yerine dışarıda bırakılır.
 */
export function seriyiVeriyeCevir(
  zamanlar: readonly string[],
  degerler: readonly (number | null)[],
): GostergeNoktasi[] {
  const noktalar: GostergeNoktasi[] = []
  const uzunluk = Math.min(zamanlar.length, degerler.length)
  for (let i = 0; i < uzunluk; i++) {
    const deger = degerler[i]
    if (deger === null) continue
    if (!Number.isFinite(deger)) continue
    noktalar.push({ time: zamanlar[i], value: deger })
  }
  return noktalar
}
