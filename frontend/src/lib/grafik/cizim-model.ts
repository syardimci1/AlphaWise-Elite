// ============================================================================
// ÇİZİM MODELİ — kullanıcı çizimlerinin SAF durum makinesi (C3, sürümlü şema)
// ============================================================================
//
// NEDEN SAF BİR REDUCER:
// Çizim aracının durumu (hangi çizimler var, hangisi seçili, geri al yığını)
// ile onun ekrana basılması BİLEREK ayrılmıştır. Grafik katmanı
// (lightweight-charts) kendi iç koordinat sistemine, canvas ölçeğine ve
// tarayıcı olaylarına bağlıdır; bu dosya HİÇBİRİNE bağlı değildir. Dolayısıyla
// burada DOM, `Date.now()`, `Math.random()` ve ağ çağrısı YOKTUR: aynı girdi
// her zaman aynı çıktıyı verir, test canvas kurmadan çalışır ve bir çizim
// hatası "render sorunu mu, veri sorunu mu" belirsizliğine düşmez.
//
// NEDEN KİMLİK (id) DIŞARIDAN GELİR:
// `Math.random()`/`Date.now()` çağrısı fonksiyonu saf olmaktan çıkarır ve
// testi zamana bağlar. Kimliği ve oluşturma damgasını üreten taraf, olayı
// başlatan arayüz katmanıdır; reducer onu YALNIZCA taşır. Böylece aynı eylem
// tekrar oynatıldığında (geri al/yinele, kayıttan yükleme) aynı durum çıkar.
//
// NEDEN `v: 1` (SÜRÜMLÜ ŞEMA):
// Çizimler kalıcı olarak saklanır ve ileride şema değişecektir. Sürüm alanı
// olmadan eski bir kayıt sessizce yanlış yorumlanır. `v` uyuşmayan kayıt
// YÜKLENMEZ — sessiz bozulma yerine görünür bir "yüklenmedi" tercih edilir.
//
// NEDEN SAHTE DEĞER ÜRETİLMEZ (Y3):
// Hesaplanamayan bir büyüklük (örn. sıfır fiyata göre yüzde değişim) `null`
// döner. 0, Infinity veya NaN ile doldurmak, arayüzde gerçek bir ölçümmüş
// gibi görüneceği için yasaktır.

/** Grafik düzleminde tek bir tutturma noktası: UTC ms epoch + fiyat. */
export type Nokta = { t_utc: number; fiyat: number }

export type CizimTipi = 'trend' | 'yatay' | 'dikey' | 'dikdortgen' | 'fib' | 'metin' | 'olcum'

export type Cizim = {
  v: 1
  id: string
  tip: CizimTipi
  noktalar: Nokta[]
  stil: { renk: string; kalinlik: number }
  metin?: string
  olusturma_utc: number
}

export type Durum = {
  cizimler: Cizim[]
  seciliId: string | null
  /** Geçmiş yığını: en yeni anlık görüntü SONDA (LIFO). */
  geri: Cizim[][]
  /** Yinele yığını: en yeni anlık görüntü SONDA (LIFO). */
  ileri: Cizim[][]
}

export type Eylem =
  | { tip: 'EKLE'; cizim: Cizim }
  | { tip: 'SEC'; id: string | null }
  | { tip: 'TASI'; id: string; dx_t: number; dy_fiyat: number }
  | { tip: 'SIL'; id: string }
  | { tip: 'GERI_AL' }
  | { tip: 'YINELE' }
  | { tip: 'TEMIZLE' }
  | { tip: 'YUKLE'; cizimler: Cizim[] }

/**
 * Her çizim tipinin gerektirdiği TAM nokta sayısı.
 *
 * NEDEN DIŞA AÇIK: arayüz katmanı da bu sayıyı bilmek zorundadır — kullanıcı
 * kaçıncı tıklamada çizimi tamamlayacak? İki yerde ayrı ayrı yazılırsa
 * (burada 2, arayüzde 3) hata sessizdir: çizim eklenir gibi görünür ama
 * doğrulamadan geçmez. Tek kaynak bu sapmayı imkânsız kılar.
 */
export const GEREKLI_NOKTA_SAYISI: Readonly<Record<CizimTipi, number>> = {
  trend: 2,
  yatay: 1,
  dikey: 1,
  dikdortgen: 2,
  fib: 2,
  metin: 1,
  olcum: 2,
}

/** Fibonacci geri çekilme oranları — sabit ve sıralı (0 = başlangıç, 1 = bitiş). */
export const FIB_SEVIYELERI: readonly number[] = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]

/** Boş başlangıç durumu. Paylaşılan bir sabit yerine fabrika: çağıran taraf
 *  kendi kopyasını alsın, yanlışlıkla ortak nesneyi değiştiremesin. */
export function bosDurum(): Durum {
  return { cizimler: [], seciliId: null, geri: [], ileri: [] }
}

/**
 * Tek bir çizimin şema geçerliliği. Geçersizse çizim SESSİZCE düzeltilmez —
 * onu taşıyan eylem tümden yok sayılır.
 */
export function gecerliCizim(cizim: Cizim): boolean {
  if (cizim.v !== 1) return false
  if (typeof cizim.id !== 'string' || cizim.id.length === 0) return false
  // Tip listede yoksa `undefined` döner; kayıttan gelen bilinmeyen bir tipi
  // burada yakalamak, çizimi ekranda hiç görünmeyen bir hayalete çevirmekten
  // iyidir. Açık `number | undefined` tipi, aramanın eksik dönebileceğini
  // derleyiciye de anlatır.
  const gereken: number | undefined = GEREKLI_NOKTA_SAYISI[cizim.tip]
  if (gereken === undefined) return false
  if (!Array.isArray(cizim.noktalar) || cizim.noktalar.length !== gereken) return false
  // NaN/Infinity içeren bir nokta tüm ölçümleri sessizce zehirler (Y3).
  //
  // ELEMANIN KENDİSİ de doğrulanmalı — bu satır 23.09.2026'da bağımsız
  // doğrulama ajanının bulduğu S1 hatasıydı: `noktalar: [null, null]` içeren
  // bir kayıt burada `TypeError: Cannot read properties of null` fırlatıyordu.
  // Kayıt localStorage'dan geliyor; kullanıcı elle düzenleyebilir, eski bir
  // sürüm ya da başka bir sekme yazmış olabilir. Yani burası GÜVENİLMEYEN
  // GİRDİ SINIRI ve bu fonksiyonun sözleşmesi "çökme yok, false dön"dür.
  // JSON'da eksik/bozuk bir nesnenin doğal gösterimi tam olarak `null`'dır.
  if (!cizim.noktalar.every((n) => nesneMi(n) && Number.isFinite(n.t_utc) && Number.isFinite(n.fiyat))) {
    return false
  }
  // STİL DOĞRULAMASI (S2): stil doğrulanmazsa `{v:1,id,tip,noktalar}` kaydı
  // GEÇERLİ sayılıyor, sonra çizim katmanı `cizim.stil.renk` okuyunca render
  // sırasında çöküyordu. Hatayı yakalaması kolay olan YÜKLEME anından,
  // yakalaması zor olan ÇİZİM anına ötelemek en kötü seçenekti.
  if (!nesneMi(cizim.stil)) return false
  if (typeof cizim.stil.renk !== 'string' || cizim.stil.renk.length === 0) return false
  if (!Number.isFinite(cizim.stil.kalinlik) || cizim.stil.kalinlik <= 0) return false
  // `metin` opsiyoneldir; VARSA dize olmalı. 'metin' tipi için ayrıca zorunlu:
  // metinsiz bir metin çizimi ekranda görünmez bir hayalettir.
  if (cizim.metin !== undefined && typeof cizim.metin !== 'string') return false
  // B2 (23.09.2026, bağımsız denetim bulgusu): burada yalnızca `typeof ===
  // 'string'` aranıyordu ve BOŞ DİZE geçiyordu. Sonuç bir "hayalet": çizim
  // ekranda GÖRÜNMÜYOR (cizimGorunumu boş metinde null döner) ama hit-test
  // onu buluyor, yani tıklanabilir/seçilebilir görünmez bir nesne oluşuyordu.
  // Arayüz bunu `girilen.trim() === ''` ile zaten engelliyordu, ama kapı
  // YANLIŞ KATMANDAYDI: localStorage'dan gelen ya da başka bir çağıranın
  // ürettiği kayıt bu kapıyı hiç görmüyordu.
  if (cizim.tip === 'metin' && (typeof cizim.metin !== 'string' || cizim.metin.trim() === '')) {
    return false
  }
  if (!Number.isFinite(cizim.olusturma_utc)) return false
  return true
}

/**
 * `typeof x === 'object'` TEK BAŞINA yetmez: `typeof null === 'object'`'tir.
 * S1 hatasının kökü tam olarak buydu, o yüzden kontrol tek bir yerde toplandı.
 */
function nesneMi(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null
}

/** Bir çizim listesinin bütün olarak geçerliliği: her öğe geçerli VE kimlikler
 *  benzersiz. Yinelenen kimlik, SIL/TASI eylemlerini belirsizleştirir. */
function gecerliCizimListesi(cizimler: Cizim[]): boolean {
  if (!Array.isArray(cizimler)) return false
  if (!cizimler.every(gecerliCizim)) return false
  return new Set(cizimler.map((c) => c.id)).size === cizimler.length
}

/**
 * Belgeyi değiştiren her eylemin ortak sonu: mevcut çizimler geçmişe itilir ve
 * yinele yığını temizlenir.
 *
 * NEDEN `ileri` TEMİZLENİR: geri alındıktan sonra yeni bir değişiklik
 * yapılırsa, ileri yığınındaki anlık görüntüler artık ulaşılamayan bir dala
 * aittir. Tutulurlarsa "yinele" kullanıcının az önce yaptığı işi sessizce yok
 * eder. Standart davranış temizlemektir.
 */
function degistir(durum: Durum, cizimler: Cizim[], seciliId: string | null): Durum {
  return { cizimler, seciliId, geri: [...durum.geri, durum.cizimler], ileri: [] }
}

/** Geçmişten gelen bir anlık görüntüde seçili çizim artık yoksa seçim düşer. */
function secimiKoru(seciliId: string | null, cizimler: Cizim[]): string | null {
  if (seciliId === null) return null
  return cizimler.some((c) => c.id === seciliId) ? seciliId : null
}

/**
 * Saf reducer: girdi durumunu ASLA mutasyona uğratmaz, her değişiklikte yeni
 * nesne döndürür. Eylem geçersizse (bilinmeyen kimlik, yanlış nokta sayısı,
 * boş yığın, etkisiz taşıma) girdi durumunun KENDİSİ döner — böylece çağıran
 * taraf referans karşılaştırmasıyla "hiçbir şey değişmedi"yi anlayabilir ve
 * gereksiz yeniden çizim yapmaz.
 */
export function reducer(durum: Durum, eylem: Eylem): Durum {
  switch (eylem.tip) {
    case 'EKLE': {
      if (!gecerliCizim(eylem.cizim)) return durum
      // Yinelenen kimlik sessiz bozulmadır: sonraki SIL/TASI hangi çizimi
      // hedeflediğini bilemez.
      if (durum.cizimler.some((c) => c.id === eylem.cizim.id)) return durum
      // Yeni çizim seçili gelir: kullanıcı onu daha yeni çizdi, tutamaçları
      // görmek için ayrıca tıklamak zorunda kalmamalı.
      return degistir(durum, [...durum.cizimler, eylem.cizim], eylem.cizim.id)
    }

    case 'SEC': {
      // Var olmayan bir kimliği seçmek, sonraki TASI/SIL'in hedefsiz kalması
      // demektir — yok sayılır.
      if (eylem.id !== null && !durum.cizimler.some((c) => c.id === eylem.id)) return durum
      if (eylem.id === durum.seciliId) return durum
      // Seçim belgeyi değiştirmez: geçmişe YAZILMAZ, `ileri` temizlenmez.
      // Yoksa bir tıklama dizisi geri al yığınını kullanılamaz hale getirir.
      return { ...durum, seciliId: eylem.id }
    }

    case 'TASI': {
      const sira = durum.cizimler.findIndex((c) => c.id === eylem.id)
      if (sira === -1) return durum
      // Etkisiz sürükleme adımı geçmişi kirletmesin.
      if (eylem.dx_t === 0 && eylem.dy_fiyat === 0) return durum
      const eski = durum.cizimler[sira]
      const yeni: Cizim = {
        ...eski,
        noktalar: eski.noktalar.map((n) => ({ t_utc: n.t_utc + eylem.dx_t, fiyat: n.fiyat + eylem.dy_fiyat })),
      }
      const liste = durum.cizimler.slice()
      liste[sira] = yeni
      return degistir(durum, liste, durum.seciliId)
    }

    case 'SIL': {
      if (!durum.cizimler.some((c) => c.id === eylem.id)) return durum
      const liste = durum.cizimler.filter((c) => c.id !== eylem.id)
      return degistir(durum, liste, durum.seciliId === eylem.id ? null : durum.seciliId)
    }

    case 'TEMIZLE': {
      if (durum.cizimler.length === 0) return durum
      // Yıkıcı bir eylemdir; geçmişe yazılır ki GERI_AL ile dönülebilsin.
      return degistir(durum, [], null)
    }

    case 'GERI_AL': {
      if (durum.geri.length === 0) return durum
      const onceki = durum.geri[durum.geri.length - 1]
      return {
        cizimler: onceki,
        seciliId: secimiKoru(durum.seciliId, onceki),
        geri: durum.geri.slice(0, -1),
        ileri: [...durum.ileri, durum.cizimler],
      }
    }

    case 'YINELE': {
      if (durum.ileri.length === 0) return durum
      const sonraki = durum.ileri[durum.ileri.length - 1]
      return {
        cizimler: sonraki,
        seciliId: secimiKoru(durum.seciliId, sonraki),
        geri: [...durum.geri, durum.cizimler],
        ileri: durum.ileri.slice(0, -1),
      }
    }

    case 'YUKLE': {
      // KISMİ yükleme YOK: listede tek bir bozuk kayıt varsa tamamı reddedilir.
      // Yarısı yüklenmiş bir çizim seti, kullanıcıya kaybı fark ettirmeden
      // üstüne kaydedilir ve veri kalıcı olarak gider.
      if (!gecerliCizimListesi(eylem.cizimler)) return durum
      // Kayıttan yükleme yeni bir belge açmaktır: önceki belgenin geri al
      // yığını bu belgede anlamsızdır, sıfırlanır.
      return { cizimler: [...eylem.cizimler], seciliId: null, geri: [], ileri: [] }
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
 * Ölçüm aracının çıktısı. `barSayisi` çağıran taraftan gelir: bar sayımı
 * takvim aritmetiği değil, grafikteki GERÇEK bar dizisinin bir özelliğidir
 * (tatiller, hafta sonları, eksik günler) — bu dosya veri setini görmez,
 * dolayısıyla uydurmaz.
 *
 * `yuzde` yüzde birimindedir (örn. 10 = %10). a.fiyat sıfır veya sonlu
 * değilse yüzde HESAPLANAMAZ ve `null` döner (Y3: sıfıra bölme uydurulmaz).
 */
export function olcumHesapla(
  a: Nokta,
  b: Nokta,
  barSayisi: number,
): { fiyatFarki: number; yuzde: number | null; barSayisi: number } {
  const fiyatFarki = b.fiyat - a.fiyat
  const yuzde = Number.isFinite(a.fiyat) && a.fiyat !== 0 ? (fiyatFarki / a.fiyat) * 100 : null
  return { fiyatFarki, yuzde, barSayisi }
}

/**
 * Fibonacci seviyeleri: oran 0 → a.fiyat, oran 1 → b.fiyat.
 *
 * NEDEN DOĞRUSAL ARA DEĞER (min/max DEĞİL): kullanıcı A'dan B'ye çizer ve
 * yön anlamlıdır. Düşüş hareketinde (a.fiyat > b.fiyat) seviyeler otomatik
 * ters sırada oluşur; min/max'a normalize etmek kullanıcının çizdiği yönü
 * sessizce değiştirirdi. Yuvarlama YAPILMAZ — gösterim katmanının işidir.
 */
export function fibSeviyeleri(a: Nokta, b: Nokta): { oran: number; fiyat: number }[] {
  const fark = b.fiyat - a.fiyat
  return FIB_SEVIYELERI.map((oran) => ({ oran, fiyat: a.fiyat + fark * oran }))
}
