// ============================================================================
// TERMİNAL DURUMU — grafik terminali bileşeninin TÜM karar mantığı (SAF)
// ============================================================================
//
// NEDEN BU DOSYA VAR:
// Bu depoda DOM testi YOKTUR (jsdom kurulu değil, kurulmayacak) ve test
// koşucusu çıplak `node:test`'tir. Bir React bileşeni burada render
// EDİLEMEZ. Dolayısıyla bileşene karar bırakmak, o kararı test edilemez
// kılmak demektir. `gosterge-tanim.ts` ile `gosterge-katmani.ts` arasındaki
// ayrımın aynısı burada da uygulanır: hangi aracın kaç tıklamada bittiği,
// zaman dilimi değişince yarım çizime ne olduğu, kullanıcıya hangi metnin
// gösterileceği — hepsi BU dosyadadır ve burada sınanır.
// `GrafikTerminali.tsx` yalnızca bu kararları uygular.
//
// SAFLIK SÖZLEŞMESİ:
//  - `Date.now()`, `Math.random()`, `localStorage`, `fetch`, DOM YOKTUR.
//    Çizim kimliği (`id`) ve oluşturma damgası (`olusturma_utc`) DIŞARIDAN
//    parametre olarak gelir; aynı girdi her koşuda aynı çıktıyı verir.
//  - Girdi durumu MUTASYONA UĞRAMAZ; değişiklik olmayan eylemde girdinin
//    KENDİSİ döner (referans karşılaştırmasıyla "değişmedi" anlaşılsın diye,
//    `cizim-model.ts` reducer'ıyla aynı sözleşme).
//
// NEDEN ARAYÜZ METİNLERİ DE BURADA (ARAYUZ_METINLERI):
// Y8 (hukuki dil) kapısı arayüzde GÖRÜNEN metinler için geçerlidir. Metinler
// .tsx içinde gömülü kalsaydı bu depoda hiçbir testle sınanamazdı — bileşen
// render edilemiyor. Metinleri saf bir tabloda toplamak, kapının gerçekten
// çalışmasını sağlayan tek yoldur; `terminal-durum.test.ts` tablonun tamamını
// yasaklı kalıp listesinden geçirir.

import type { KaydetSonucu } from './cizim-kalicilik'
import type { Cizim, CizimTipi, Nokta } from './cizim-model'
import { GEREKLI_NOKTA_SAYISI, gecerliCizim } from './cizim-model'
import type { GostergeKimlik } from './gosterge-tanim'
import { tumGostergeKimlikleri } from './gosterge-tanim'
import type { ZamanDilimi } from './zaman-dilimi'

/** Araç çubuğundaki seçim: ya imleç (seçme/inceleme) ya da bir çizim tipi. */
export type AracKimlik = 'imlec' | CizimTipi

export type TerminalDurum = {
  dilim: ZamanDilimi
  arac: AracKimlik
  /** Açık göstergeler; sırası `tumGostergeKimlikleri()` sırasına normalize edilir. */
  gostergeler: GostergeKimlik[]
  /** Çizim tamamlanana kadar biriken tıklama noktaları. */
  bekleyenNoktalar: Nokta[]
}

export type TerminalEylem =
  | { tip: 'ARAC_SEC'; arac: AracKimlik }
  | { tip: 'DILIM_SEC'; dilim: ZamanDilimi }
  | { tip: 'GOSTERGE_DEGISTIR'; kimlik: GostergeKimlik }
  /** Kayıtlı seçimi uygular (ADR-5): sembol/kullanıcı değişince önceki seçimin YERİNE geçer. */
  | { tip: 'GOSTERGELERI_YUKLE'; gostergeler: readonly GostergeKimlik[] }
  | { tip: 'NOKTA_EKLE'; nokta: Nokta }
  | { tip: 'CIZIM_IPTAL' }

/**
 * Yeni bir çizim için gereken, bu dosyanın ÜRETEMEYECEĞİ bilgiler.
 *
 * Görev tanımındaki imza `tiklamaSonucu(durum, nokta)` idi; buraya üçüncü bir
 * parametre BİLEREK eklendi. Gerekçe: `Cizim` şeması `id`, `olusturma_utc` ve
 * `stil` alanlarını ZORUNLU tutar (bkz. cizim-model.gecerliCizim) ve 'metin'
 * tipi ayrıca metin ister. Bunları burada üretmek `Math.random()`/`Date.now()`
 * çağırmak olurdu — yani tam olarak yasaklanan şey. Üreten taraf arayüz
 * katmanıdır; bu dosya yalnızca taşır.
 */
export type CizimKimligi = {
  id: string
  olusturma_utc: number
  stil: { renk: string; kalinlik: number }
  metin?: string
}

export type TiklamaSonucu = {
  yeniDurum: TerminalDurum
  tamamlananCizim?: Cizim
  /**
   * Tıklama işlenemediyse kullanıcıya GÖSTERİLECEK sebep. Sessiz yutma yok:
   * "tıkladım ama hiçbir şey olmadı" durumu her zaman açıklanır.
   */
  hata?: string
}

/** Araç çubuğundaki gösterim sırası. İmleç başta: varsayılan araç odur. */
export const ARAC_SIRASI: readonly AracKimlik[] = [
  'imlec',
  'trend',
  'yatay',
  'dikey',
  'dikdortgen',
  'fib',
  'metin',
  'olcum',
]

/** Desteklenen zaman dilimleri — hepsi GÜNLÜK bardan türetilebilir olanlar. */
export const DILIM_SIRASI: readonly ZamanDilimi[] = ['gunluk', 'haftalik', 'aylik']

/**
 * Arayüzde devre dışı gösterilecek gün içi dilimler.
 *
 * NEDEN DÜĞME OLARAK DURUYORLAR: ADR-3'e göre gün içi veri kaynağı yoktur.
 * Düğmeleri hiç göstermemek "bu ürün gün içi destekliyor olabilir, ben
 * bulamadım" belirsizliği bırakırdı; devre dışı düğme + sebep etiketi
 * eksikliği AÇIKÇA söyler (Y3: olmayan veri, varmış gibi sunulmaz).
 */
export const GUN_ICI_DILIMLER: readonly string[] = ['1 dk', '5 dk', '15 dk', '1 sa', '4 sa']

/** Gün içi düğmelerinin `title` metni ve devre dışı olma sebebi. */
export function gunIciNeden(): string {
  return 'Gün içi veri kaynağı yok'
}

/** Araç çubuğu etiketleri. Tamamı TARİFSELDİR (Y8). */
export const ARAC_ETIKETLERI: Readonly<Record<AracKimlik, string>> = {
  imlec: 'İmleç',
  trend: 'Trend çizgisi',
  yatay: 'Yatay çizgi',
  dikey: 'Dikey çizgi',
  dikdortgen: 'Dikdörtgen',
  fib: 'Fibonacci seviyeleri',
  metin: 'Metin notu',
  olcum: 'Ölçüm',
}

export const DILIM_ETIKETLERI: Readonly<Record<ZamanDilimi, string>> = {
  gunluk: 'Günlük',
  haftalik: 'Haftalık',
  aylik: 'Aylık',
}

/**
 * Bileşende GÖRÜNEN sabit metinlerin tamamı.
 *
 * Y8 testi bu tablonun TÜM değerlerini tarar; .tsx içine gömülü bir metin
 * kapıdan kaçardı. Bu yüzden `GrafikTerminali.tsx` sabit metin YAZMAZ,
 * buradan okur.
 */
export const ARAYUZ_METINLERI = {
  baslik: 'Grafik terminali',
  zamanDilimi: 'Zaman dilimi',
  araclar: 'Çizim araçları',
  gostergeler: 'Göstergeler',
  geriAl: 'Geri alma',
  geriAlAria: 'Son çizim işlemini geri alma',
  yinele: 'Yineleme',
  yineleAria: 'Geri alma işlemini yineleme',
  temizle: 'Temizle',
  temizleAria: 'Tüm çizimleri silme',
  png: 'PNG',
  pngAria: 'Grafiği PNG dosyası olarak indirme',
  yukleniyor: 'Fiyat verisi okunuyor…',
  veriYok: 'Bu sembol için gösterilecek fiyat barı yok.',
  veriHatasi: 'Fiyat verisi okunamadı',
  bayrakHatasi: 'Grafik terminali ayarı okunamadı',
  kayitHatasi: 'Çizimler tarayıcı deposuna yazılamadı',
  pngHatasi: 'PNG dosyası üretilemedi',
  metinIstemi: 'Not metni:',
  noktaHesaplanamadi: 'Tıklanan konum veri aralığının dışında; nokta eklenmedi.',
  cizimGecersiz: 'Çizim şemaya uymadığı için eklenmedi.',
  // B4 (23.09.2026, bağımsız denetim): bileşen `Backspace` ile de siliyor
  // ama ipucu yalnızca `Delete` diyordu — belgelenmemiş YIKICI tuş.
  klavyeIpucu: 'Delete veya Backspace = seçili çizimi silme · Escape = çizimi bırakma',
  // Kimlik çekilemezse çizimler yüklenmez/kaydedilmez. Sessiz kalmak yerine
  // söylüyoruz: kullanıcı çizimlerinin neden görünmediğini bilmeli.
  kimlikHatasi: 'Kullanıcı kimliği okunamadı, çizimler bu oturumda saklanmayacak',
  gostergeKayitHatasi: 'Gösterge seçimi tarayıcı deposuna yazılamadı',
  karsilastirmaKayitHatasi: 'Karşılaştırma seçimi tarayıcı deposuna yazılamadı',
  kayitliKarsilastirma: 'Kayıtlı karşılaştırma',
  kotaDolu: 'tarayıcı deposu dolu. Değişiklik bu sekmede görünmeye devam ediyor ama sayfa yenilenirse kaybolur; yer açmak için başka sembollerdeki eski çizimler silinebilir.',
  kayitliCizimler: 'Kayıtlı çizimler',
  kayitliGostergeler: 'Kayıtlı göstergeler',
  sifirla: 'Kayıtlı ayarları sıfırla',
  sifirlaAria: 'Bu sembol için kayıtlı gösterge, çizim ve karşılaştırma ayarlarını silme',
  sifirlaOnay: 'Bu sembol için kayıtlı göstergeler, çizimler ve karşılaştırma sembolleri silinecek. Bu işlem geri döndürülemez. Devam edilsin mi?',
  sifirlandi: 'Bu sembol için kayıtlı ayarlar silindi.',
  sifirlamaHatasi: 'Kayıtlı ayarlar silinemedi',
  baskaSekme: 'Bu sembolün kayıtlı ayarları başka bir sekmede değişti; bu sekmedeki bir sonraki değişiklik onların üzerine yazacak. Güncel hali görmek için sayfa yenilenebilir.',
} as const

/** Türetilmemiş (kaynak) veri notu — Y3: türetilmiş veri yerli gibi sunulmaz. */
const YERLI_NOTU = 'kaynak veri (türetilmedi)'
const TURETILDI_NOTU = 'günlük barlardan türetildi'
const EKSIK_KOVA_NOTU = 'son dönem henüz tamamlanmadı'

/** Boş başlangıç durumu. Paylaşılan sabit değil fabrika (bkz. cizim-model.bosDurum). */
export function bosTerminalDurum(): TerminalDurum {
  return { dilim: 'gunluk', arac: 'imlec', gostergeler: [], bekleyenNoktalar: [] }
}

/**
 * Saf reducer. Etkisiz eylemde girdi durumunun KENDİSİ döner.
 *
 * NEDEN ARAÇ/DİLİM DEĞİŞİNCE BEKLEYEN NOKTALAR DÜŞER:
 * - Araç: yarım kalmış bir dikdörtgenin ilk köşesi, sonra seçilen "yatay
 *   çizgi" aracı için anlamsızdır; taşınsaydı kullanıcı hiç tıklamadığı bir
 *   yere çizgi çizilmiş bulurdu.
 * - Dilim: haftalığa geçince grafikte yalnızca kova barları vardır; günlük
 *   bir tarihe tutturulmuş yarım nokta `timeToCoordinate` ile karşılık
 *   bulamaz ve görünmez bir hayalete dönüşürdü.
 */
export function terminalReducer(durum: TerminalDurum, eylem: TerminalEylem): TerminalDurum {
  switch (eylem.tip) {
    case 'ARAC_SEC': {
      if (eylem.arac === durum.arac) return durum
      return { ...durum, arac: eylem.arac, bekleyenNoktalar: [] }
    }

    case 'DILIM_SEC': {
      if (eylem.dilim === durum.dilim) return durum
      return { ...durum, dilim: eylem.dilim, bekleyenNoktalar: [] }
    }

    case 'GOSTERGE_DEGISTIR': {
      const kume = new Set<GostergeKimlik>(durum.gostergeler)
      if (kume.has(eylem.kimlik)) kume.delete(eylem.kimlik)
      else kume.add(eylem.kimlik)
      // Sıra KANONİK tutulur: aç-kapa sırasına göre dizilseydi aynı iki
      // gösterge farklı sıralarda çizilir, alt panellerin yeri her tıklamada
      // değişirdi.
      return { ...durum, gostergeler: tumGostergeKimlikleri().filter((k) => kume.has(k)) }
    }

    case 'GOSTERGELERI_YUKLE': {
      const kume = new Set<GostergeKimlik>(eylem.gostergeler)
      const yeni = tumGostergeKimlikleri().filter((k) => kume.has(k))
      // Aynı içerik → girdinin kendisi: yeniden render ve gereksiz kayıt tetiklenmez.
      if (yeni.length === durum.gostergeler.length && yeni.every((k, i) => k === durum.gostergeler[i])) {
        return durum
      }
      return { ...durum, gostergeler: yeni }
    }

    case 'NOKTA_EKLE': {
      // İmleç bir çizim aracı değildir: seçim yapar, nokta biriktirmez.
      if (durum.arac === 'imlec') return durum
      // NaN/Infinity bir noktayı sessizce zehirler (Y3); kapıda tutulur.
      if (!Number.isFinite(eylem.nokta.t_utc) || !Number.isFinite(eylem.nokta.fiyat)) return durum
      const gereken = GEREKLI_NOKTA_SAYISI[durum.arac]
      // Normal akışta `tiklamaSonucu` doluluğu görüp listeyi boşaltır; bu kapı
      // reducer'ın DOĞRUDAN çağrıldığı durumda fazla noktayı engeller — aksi
      // halde şema doğrulaması (nokta sayısı TAM eşleşmeli) çizimi reddederdi.
      if (durum.bekleyenNoktalar.length >= gereken) return durum
      return { ...durum, bekleyenNoktalar: [...durum.bekleyenNoktalar, eylem.nokta] }
    }

    case 'CIZIM_IPTAL': {
      if (durum.bekleyenNoktalar.length === 0) return durum
      return { ...durum, bekleyenNoktalar: [] }
    }

    default: {
      // Yeni bir eylem tipi eklenip burada karşılıksız kalırsa DERLEME hatası
      // verir; çalışma zamanında sessizce yok sayılmaz.
      const eksikEylem: never = eylem
      void eksikEylem
      return durum
    }
  }
}

/**
 * Grafik üzerindeki tek bir tıklamanın sonucu.
 *
 * Aracın gerektirdiği kadar nokta birikince çizim TAMAMLANIR ve bekleyen
 * liste boşalır. ARAÇ SEÇİLİ KALIR: kullanıcı arka arkaya birden çok trend
 * çizgisi çizebilmeli, her çizimden sonra aracı yeniden seçmek zorunda
 * kalmamalıdır.
 *
 * Üretilen çizim `gecerliCizim`'den GEÇMEDEN dönmez: geçersiz bir çizim
 * `cizim-model` reducer'ında sessizce yok sayılırdı ve kullanıcı neden hiçbir
 * şey olmadığını anlayamazdı. Burada reddedilir ve sebep `hata` ile döner.
 */
export function tiklamaSonucu(
  durum: TerminalDurum,
  nokta: Nokta,
  kimlik: CizimKimligi,
): TiklamaSonucu {
  if (durum.arac === 'imlec') return { yeniDurum: durum }

  if (!Number.isFinite(nokta.t_utc) || !Number.isFinite(nokta.fiyat)) {
    return { yeniDurum: durum, hata: ARAYUZ_METINLERI.noktaHesaplanamadi }
  }

  const sonrasi = terminalReducer(durum, { tip: 'NOKTA_EKLE', nokta })
  const gereken = GEREKLI_NOKTA_SAYISI[durum.arac]
  if (sonrasi.bekleyenNoktalar.length < gereken) return { yeniDurum: sonrasi }

  const cizim: Cizim = {
    v: 1,
    id: kimlik.id,
    tip: durum.arac,
    noktalar: [...sonrasi.bekleyenNoktalar],
    stil: { renk: kimlik.stil.renk, kalinlik: kimlik.stil.kalinlik },
    olusturma_utc: kimlik.olusturma_utc,
  }
  if (kimlik.metin !== undefined) cizim.metin = kimlik.metin

  if (!gecerliCizim(cizim)) {
    // Girdi durumu OLDUĞU GİBİ döner: yarım nokta birikimi ilerletilmez,
    // kullanıcı aynı tıklamayı düzelttikten sonra tekrar deneyebilir.
    return { yeniDurum: durum, hata: ARAYUZ_METINLERI.cizimGecersiz }
  }

  return { yeniDurum: { ...sonrasi, bekleyenNoktalar: [] }, tamamlananCizim: cizim }
}

/**
 * Zaman dilimi durum etiketi.
 *
 * Y3 GEREĞİ: "türetildi" ve "son dönem henüz tamamlanmadı" bilgileri AÇIKÇA
 * yazılır. Haftalık bar, günlük barlardan hesaplanmış bir TÜRETMEDİR; borsadan
 * gelen yerli bir haftalık bar gibi sunulursa kullanıcı onu kaynak veri sanar.
 * Aynı şekilde devam eden hafta/ay kapanmamıştır; "eksik" olduğu söylenmezse
 * son bar tamamlanmış bir periyot zannedilir.
 *
 * Metin YALNIZCA verilen bayraklardan üretilir — dilime bakıp "günlük zaten
 * türetilmez" gibi bir varsayım YAPILMAZ; çağıran ne ölçtüyse o yazılır.
 */
export function dilimEtiketi(
  dilim: ZamanDilimi,
  turetildi: boolean,
  eksikSonKova: boolean,
): string {
  const parcalar: string[] = [DILIM_ETIKETLERI[dilim]]
  parcalar.push(turetildi ? TURETILDI_NOTU : YERLI_NOTU)
  if (eksikSonKova) parcalar.push(EKSIK_KOVA_NOTU)
  return parcalar.join(' · ')
}

/**
 * Atlanan kayıtların kullanıcıya görünen notu; atlanan yoksa `null`.
 *
 * `hamBarlariCevir` ve `resample` kaç kaydı elediklerini RAPORLUYOR; bu sayı
 * arayüze taşınmazsa veri sessizce eksilmiş olur (deponun "sessiz yutma
 * yasağı"). Grafik eksik bir seriyi tam gibi gösteremez.
 */
export function veriNotu(atlananHam: number, atlananDilim: number): string | null {
  const parcalar: string[] = []
  if (atlananHam > 0) parcalar.push(`${atlananHam} kayıt biçimi bozuk olduğu için atlandı`)
  if (atlananDilim > 0) parcalar.push(`${atlananDilim} bar tarihi geçersiz olduğu için atlandı`)
  return parcalar.length === 0 ? null : parcalar.join(' · ')
}

/**
 * Kayıttan yüklemenin kullanıcıya görünen notu; uyarı yoksa `null`.
 *
 * İki kayıt (çizim, gösterge) ayrı okunur ve ikisi de "sıfırlandı" diyebilir;
 * önek olmadan kullanıcı hangi ayarının gittiğini anlayamazdı (C4: sessiz
 * kayıp yok, belirsiz kayıp da yok).
 */
export function yuklemeNotu(
  cizimUyarisi: string | undefined,
  gostergeUyarisi: string | undefined,
): string | null {
  const parcalar: string[] = []
  if (cizimUyarisi) parcalar.push(`${ARAYUZ_METINLERI.kayitliCizimler}: ${cizimUyarisi}`)
  if (gostergeUyarisi) parcalar.push(`${ARAYUZ_METINLERI.kayitliGostergeler}: ${gostergeUyarisi}`)
  return parcalar.length === 0 ? null : parcalar.join(' · ')
}

/**
 * Kaydetme sonucunun kullanıcıya görünen metni; başarıda boş dizge.
 *
 * Y9: kota dolunca teknik hata adı (`QuotaExceededError`) kullanıcıya bir şey
 * söylemez; ne olduğunu, sonucunu ve ne yapılabileceğini söyleyen metin
 * gösterilir. Kota dışı hatalarda teknik ayrıntı KORUNUR — tanı için gerekir.
 */
export function kayitHataMetni(tur: 'cizim' | 'gosterge' | 'karsilastirma', sonuc: KaydetSonucu): string {
  if (sonuc.basarili) return ''
  const onek =
    tur === 'cizim'
      ? ARAYUZ_METINLERI.kayitHatasi
      : tur === 'gosterge'
        ? ARAYUZ_METINLERI.gostergeKayitHatasi
        : ARAYUZ_METINLERI.karsilastirmaKayitHatasi
  return `${onek}: ${sonuc.kotaDoldu === true ? ARAYUZ_METINLERI.kotaDolu : sonuc.hata ?? ''}`
}
