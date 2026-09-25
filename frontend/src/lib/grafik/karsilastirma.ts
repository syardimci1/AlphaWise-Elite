// ============================================================================
// KARŞILAŞTIRMA MODU — seçim, hizalama, yüzde normalize, çizgi verisi, lejant (SAF)
// ============================================================================
//
// Sözleşme: contracts/grafik/karsilastirma_modu.md · Karar: ADR-6.
//
// NEDEN SAF: bileşen render edilemiyor (jsdom yok, bkz. terminal-durum.ts).
// "Normalize doğru mu, yanıltıcı mı?" sorusunun cevabı (Y3) burada verilir ve
// burada sınanır; `GrafikTerminali.tsx` yalnızca sonucu grafiğe basar.
//
// SAFLIK SÖZLEŞMESİ: Date.now(), Math.random(), localStorage, fetch, DOM YOK.
// Girdi mutasyona uğramaz; etkisiz işlemde girdinin KENDİSİ döner.

/** Renk yuvası: 0 her zaman ana sembol, 1–2 ek semboller (C3). */
export type Yuva = 0 | 1 | 2

export type KapanisBari = { tarih: string; kapanis: number }

export type GirdiSerisi = {
  sembol: string
  yuva: Yuva
  barlar: readonly KapanisBari[]
}

export type HizaliSeri = {
  sembol: string
  yuva: Yuva
  /** Eksenle BİRE BİR hizalı yüzde değerleri; `null` = o gün bu seride veri yok. */
  degerler: (number | null)[]
  tabanKapanis: number
  /** Taban ile serinin son barı arasında, eksende olup bu seride olmayan günler (C4). */
  eksikTarihler: string[]
  /** Ortak taban gününden önce kalıp grafiğe girmeyen bar sayısı (C1). */
  tabanOncesi: number
  /** Sonlu olmayan / ≤ 0 kapanış ya da yinelenen tarih yüzünden yok sayılan bar sayısı. */
  gecersizKapanis: number
  /** Önceki geçerli bara göre |değişim| > BUYUK_SICRAMA_ESIGI olan günler (bölünme/veri hatası olabilir). */
  buyukSicramaTarihleri: string[]
  /** Serinin son geçerli barının tarihi. */
  sonTarih: string
}

export type HizalamaSonucu =
  | { durum: 'tamam'; tabanTarihi: string; eksen: string[]; seriler: HizaliSeri[] }
  /** Geçerli verisi olan seri sayısı < 2: karşılaştırma anlamsız, tek seri gösterimine düşülür. */
  | { durum: 'yetersiz'; verisiz: string[] }
  /** Tarih aralıkları kesişmiyor: ortak bir %0 günü yok. */
  | { durum: 'ortak-gun-yok'; verisiz: string[] }

/**
 * Tek günlük |değişim| eşiği. Düzeltilmemiş 2:1 bölünme −%50, 3:1 −%66 görünür;
 * büyük endekslerde tek gün %40 hareket son derece nadirdir. Eşik bir İŞARETTİR,
 * veri değiştirmez: kaynak düzeltmesi doğrulanamadığı için (FAZ 1 §3.2) iddia yok.
 */
export const BUYUK_SICRAMA_ESIGI = 0.4

const GUN_DESENI = /^\d{4}-\d{2}-\d{2}$/

function gecerliKapanis(kapanis: number): boolean {
  return Number.isFinite(kapanis) && kapanis > 0
}

type TemizSeri = { girdi: GirdiSerisi; harita: Map<string, number>; tarihler: string[]; gecersiz: number }

/**
 * Seriyi sıralar, geçersiz barları ayıklar ve sayar. Yinelenen tarihte İLK gelen
 * kalır (hangisinin doğru olduğu bilinemez; ikisini ortalamak uydurmak olurdu).
 */
function temizle(girdi: GirdiSerisi): TemizSeri {
  const harita = new Map<string, number>()
  let gecersiz = 0
  for (const bar of girdi.barlar) {
    if (typeof bar.tarih !== 'string' || !GUN_DESENI.test(bar.tarih) || harita.has(bar.tarih)) {
      gecersiz += 1
      continue
    }
    if (!gecerliKapanis(bar.kapanis)) {
      gecersiz += 1
      continue
    }
    harita.set(bar.tarih, bar.kapanis)
  }
  // "YYYY-MM-DD" sözlük sırası = kronolojik sıra.
  const tarihler = [...harita.keys()].sort()
  return { girdi, harita, tarihler, gecersiz }
}

/**
 * C1 + C4: ortak taban gününü bulur, serileri ortak eksene hizalar ve yüzdeye çevirir.
 *
 * - Taban = tüm serilerde geçerli kapanış olan İLK gün (en geç başlayan serinin
 *   ilk gününden aranır). Her seri tabanda tam %0.
 * - Eksen = taban sonrası herhangi bir seride geçerli barı olan günlerin birleşimi.
 * - Eksik gün `null` kalır: enterpolasyon YOK, son değer taşıma YOK (Y9).
 */
export function hizalaVeNormalizeEt(girdiler: readonly GirdiSerisi[]): HizalamaSonucu {
  const temizler = girdiler.map(temizle)
  const verisiz = temizler.filter((t) => t.tarihler.length === 0).map((t) => t.girdi.sembol)
  const dolular = temizler.filter((t) => t.tarihler.length > 0)
  if (dolular.length < 2) return { durum: 'yetersiz', verisiz }

  const enGecBaslangic = dolular.map((t) => t.tarihler[0]).sort()[dolular.length - 1]
  // Aday günler: en geç başlayan serinin kendi günleri (taban onun ilk ortak günüdür).
  const enGecSeri = dolular.find((t) => t.tarihler[0] === enGecBaslangic) as TemizSeri
  const tabanTarihi = enGecSeri.tarihler.find((gun) => dolular.every((t) => t.harita.has(gun)))
  if (tabanTarihi === undefined) return { durum: 'ortak-gun-yok', verisiz }

  const birlesim = new Set<string>()
  for (const t of dolular) for (const gun of t.tarihler) if (gun >= tabanTarihi) birlesim.add(gun)
  const eksen = [...birlesim].sort()

  const seriler: HizaliSeri[] = dolular.map((t) => {
    const tabanKapanis = t.harita.get(tabanTarihi) as number
    const sonTarih = t.tarihler[t.tarihler.length - 1]
    const degerler: (number | null)[] = []
    const eksikTarihler: string[] = []
    const buyukSicramaTarihleri: string[] = []
    let onceki: number | null = null
    for (const gun of eksen) {
      const kapanis = t.harita.get(gun)
      if (kapanis === undefined) {
        degerler.push(null)
        // Son bardan SONRASI boşluk değil, serinin bitişidir (sonTarih ile raporlanır).
        if (gun < sonTarih) eksikTarihler.push(gun)
        continue
      }
      // Taban günü TAM 0 olsun: (x/x − 1)·100 zaten 0'dır, ama açık yazmak
      // kayan nokta sürprizine yer bırakmaz.
      degerler.push(gun === tabanTarihi ? 0 : (kapanis / tabanKapanis - 1) * 100)
      if (onceki !== null && Math.abs(kapanis / onceki - 1) > BUYUK_SICRAMA_ESIGI) buyukSicramaTarihleri.push(gun)
      onceki = kapanis
    }
    return {
      sembol: t.girdi.sembol,
      yuva: t.girdi.yuva,
      degerler,
      tabanKapanis,
      eksikTarihler,
      tabanOncesi: t.tarihler.filter((gun) => gun < tabanTarihi).length,
      gecersizKapanis: t.gecersiz,
      buyukSicramaTarihleri,
      sonTarih,
    }
  })

  return { durum: 'tamam', tabanTarihi, eksen, seriler }
}

// ---------------------------------------------------------------------------
// S1 / S6 — seçim: ekleme, çıkarma, mod (C2, C3, C6)
// ---------------------------------------------------------------------------

/** Grup üst sınırı: ana sembol + 2 ek (C2, ADR-6). */
export const AZAMI_GRUP = 3
const EK_YUVALAR: readonly Exclude<Yuva, 0>[] = [1, 2]

export type GorunumModu = 'tek' | 'karsilastirma'
export type EkSembol = { sembol: string; yuva: Exclude<Yuva, 0> }
export type KarsilastirmaSecimi = { mod: GorunumModu; semboller: EkSembol[] }

export type EklemeRet = 'gecersiz' | 'ana' | 'yinelenen' | 'dolu'
export type EklemeSonucu =
  | { tamam: true; secim: KarsilastirmaSecimi }
  | { tamam: false; neden: EklemeRet; metin: string }

/**
 * Arayüzde GÖRÜNEN karşılaştırma metinleri. Y8 testi tablonun tamamını
 * yasaklı kalıp listesinden geçirir (bkz. terminal-durum.ARAYUZ_METINLERI).
 */
export const KARSILASTIRMA_METINLERI = {
  gorunum: 'Görünüm',
  tekMod: 'Tek sembol',
  karsilastirmaMod: 'Karşılaştırma',
  sembolEtiketi: 'Karşılaştırılacak sembol',
  ekle: 'Ekle',
  ekleAria: 'Sembolü karşılaştırmaya ekleme',
  cikarAria: 'Karşılaştırmadan çıkar',
  anaSembol: 'ana sembol',
  gecersiz: 'Sembol biçimi geçersiz (harf/rakam, arada tek nokta ya da tire, en fazla 10 karakter).',
  ana: 'Bu sembol zaten ana sembol; kendisiyle karşılaştırılamaz.',
  yinelenen: 'Bu sembol karşılaştırmada zaten var.',
  dolu: `Karşılaştırmada en fazla ${AZAMI_GRUP} sembol olabilir; yeni sembol için önce birini çıkarın.`,
  doluNeden: `En fazla ${AZAMI_GRUP} sembol`,
} as const

/** Aynı desen: servis-proxy.tickerDogrula (sunucu kodu, istemciye alınamaz). Eşdeğerlik testle kilitli. */
const TICKER_DESENI = /^[A-Z0-9]+(?:[.-][A-Z0-9]+)*$/
const TICKER_MAKS_UZUNLUK = 10

/** Kırpar, büyük harfe çevirir (yerelden bağımsız), biçimi doğrular; geçersizse null. */
export function sembolNormalize(ham: string): string | null {
  const t = (typeof ham === 'string' ? ham : '').trim().toUpperCase()
  if (t.length === 0 || t.length > TICKER_MAKS_UZUNLUK) return null
  return TICKER_DESENI.test(t) ? t : null
}

export function bosSecim(): KarsilastirmaSecimi {
  return { mod: 'tek', semboller: [] }
}

/**
 * Ek sembol ekler. 3 doluysa REDDEDER (en eskiyi çıkarmaz — ADR-6): kullanıcının
 * seçimi onun haberi olmadan değişmemeli. Yeni sembol en düşük boş yuvayı alır.
 */
export function sembolEkle(secim: KarsilastirmaSecimi, anaSembol: string, ham: string): EklemeSonucu {
  const sembol = sembolNormalize(ham)
  if (sembol === null) return { tamam: false, neden: 'gecersiz', metin: KARSILASTIRMA_METINLERI.gecersiz }
  if (sembol === anaSembol.trim().toUpperCase()) {
    return { tamam: false, neden: 'ana', metin: KARSILASTIRMA_METINLERI.ana }
  }
  if (secim.semboller.some((s) => s.sembol === sembol)) {
    return { tamam: false, neden: 'yinelenen', metin: KARSILASTIRMA_METINLERI.yinelenen }
  }
  const dolu = new Set(secim.semboller.map((s) => s.yuva))
  const yuva = EK_YUVALAR.find((y) => !dolu.has(y))
  if (yuva === undefined) return { tamam: false, neden: 'dolu', metin: KARSILASTIRMA_METINLERI.dolu }
  return { tamam: true, secim: { ...secim, semboller: [...secim.semboller, { sembol, yuva }] } }
}

/** Ek sembolü çıkarır; diğerlerinin yuvası (rengi) DEĞİŞMEZ (C3). Yoksa girdinin kendisi. */
export function sembolCikar(secim: KarsilastirmaSecimi, sembol: string): KarsilastirmaSecimi {
  const kalan = secim.semboller.filter((s) => s.sembol !== sembol)
  return kalan.length === secim.semboller.length ? secim : { ...secim, semboller: kalan }
}

/** Mod değiştirir; liste KORUNUR (C6). Aynı mod → girdinin kendisi. */
export function modSec(secim: KarsilastirmaSecimi, mod: GorunumModu): KarsilastirmaSecimi {
  return secim.mod === mod ? secim : { ...secim, mod }
}

/** Grup dolu mu (ekleme düğmesi devre dışı + neden). */
export function grupDolu(secim: KarsilastirmaSecimi): boolean {
  return secim.semboller.length + 1 >= AZAMI_GRUP
}
