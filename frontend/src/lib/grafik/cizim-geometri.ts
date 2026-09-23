// ============================================================================
// ÇİZİM GEOMETRİSİ — ekran koordinatı, uzaklık ve görünüm hesabı (SAF)
// ============================================================================
//
// NEDEN AYRI BİR DOSYA:
// Çizimlerin ekrana basılması iki ayrı işten oluşur: (1) "bu çizim ekranda
// NEREDE duruyor / imleç ona NE KADAR yakın" hesabı, (2) canvas'a boya sürme.
// (2) tarayıcıya ve lightweight-charts'a bağımlıdır, bu depoda test EDİLEMEZ
// (jsdom yok, canvas yok). (1) ise saf aritmetiktir. İkisi aynı dosyada
// olsaydı hesabın tamamı test edilemez hale gelirdi. Bu yüzden TÜM hesap
// buradadır ve `cizim-primitive.ts` yalnızca buradan çıkan sonuçları boyar.
//
// NEDEN `Donusum` ARAYÜZÜ (kütüphane tipi DEĞİL):
// Bu dosya lightweight-charts'ı İTHAL ETMEZ. Grafik kütüphanesinden ihtiyaç
// duyulan tek şey iki dönüşümdür: zaman -> x, fiyat -> y. Bunlar küçük bir
// arayüzün arkasına alındığında testler gerçek bir grafik örneği kurmadan,
// elle yazılmış deterministik bir dönüşümle çalışır. İmleç isabetini
// doğrulamak için canvas açmak gerekmez.
//
// NEDEN `null` DÖNÜLÜR (Y3):
// Kütüphane, verisi olmayan bir zaman ya da ölçek dışı bir fiyat için
// koordinat ÜRETEMEZ ve `null` döner. Bunu 0'a çevirmek çizimi sol üst köşeye
// yapıştırır: kullanıcı ekranda GERÇEK sanacağı bir konum görür. Hesaplanamayan
// konum burada da `null`'dır; çizilmeyen bir çizim, yanlış yerde duran bir
// çizimden iyidir.

import type { Cizim, Nokta } from './cizim-model'
import { fibSeviyeleri, olcumHesapla } from './cizim-model'

/**
 * Grafik düzleminden ekran düzlemine iki yönlü olmayan (tek yön) dönüşüm.
 * Uygulaması `cizim-primitive.ts`'tedir; testlerde elle yazılır.
 * Koordinat üretilemiyorsa `null` döner (bkz. dosya başlığı).
 */
export type Donusum = {
  zamanX(t_utc: number): number | null
  fiyatY(fiyat: number): number | null
}

/** CSS (media) piksel cinsinden ekran konumu. Bitmap ölçeğine çevirme işi
 *  boyayan katmanın sorumluluğudur — burada piksel oranı BİLİNMEZ. */
export type EkranNoktasi = { x: number; y: number }

/**
 * İmleç isabet eşiği (CSS pikseli). Tek yerde tanımlıdır: isabet testi
 * `cizim-primitive.hitTest` içinde yapılır ama eşiğin kendisi buradaki
 * uzaklık ölçüleriyle aynı birimdedir; iki dosyaya ayrı ayrı yazılırsa
 * biri değişip diğeri kalabilir.
 */
export const HIT_ESIK_PX = 8

/** Tek bir Fibonacci seviyesinin ekrandaki karşılığı. */
export type FibCizgisi = {
  oran: number
  fiyat: number
  y: number
  /**
   * Etiket metni. YALNIZCA sayıdır (örn. "0.382").
   * NEDEN: Y8 — arayüz metni tarifsel kalmalıdır; "destek", "giriş bölgesi",
   * "hedef" gibi yorum/tavsiye sözcükleri seviye etiketine YAZILMAZ.
   */
  etiket: string
}

/**
 * Bir çizimin ekranda kapladığı geometrik biçim — boyama katmanının tek
 * girdisi. `Cizim` alan adlarından (t_utc/fiyat) BİLEREK farklıdır: buradaki
 * her değer artık piksel'dir, veri değil.
 */
export type Gorunum =
  | { tip: 'segment'; a: EkranNoktasi; b: EkranNoktasi; etiket: string | null }
  | { tip: 'yatay'; y: number }
  | { tip: 'dikey'; x: number }
  | { tip: 'dikdortgen'; a: EkranNoktasi; b: EkranNoktasi }
  | { tip: 'fib'; cizgiler: FibCizgisi[] }
  | { tip: 'metin'; nokta: EkranNoktasi; metin: string }

/** Nokta dizisinden güvenli okuma: bozuk/eksik kayıt burada `null` olur,
 *  aşağıdaki hesaplar `undefined.fiyat` ile çökmez. */
function noktaAl(cizim: Cizim, sira: number): Nokta | null {
  if (!Array.isArray(cizim.noktalar)) return null
  return sira < cizim.noktalar.length ? cizim.noktalar[sira] : null
}

/**
 * Dönüşümden gelen değerin gerçekten kullanılabilir bir koordinat olup
 * olmadığı. NaN/Infinity, tüm uzaklık ölçülerini sessizce zehirler (Y3).
 *
 * NEDEN TİP KORUYUCU (`deger is number`): çıplak `boolean` döndürseydi
 * derleyici, kontrolden SONRA değerin hâlâ `null` olabileceğini düşünürdü;
 * her çağrı yerinde ikinci bir kontrol ya da bir zorlama gerekirdi.
 */
function sayiVarMi(deger: number | null): deger is number {
  return deger !== null && Number.isFinite(deger)
}

/** Grafik noktasını ekran noktasına çevirir; biri bile üretilemiyorsa `null`. */
export function ekranNoktasi(nokta: Nokta, dnm: Donusum): EkranNoktasi | null {
  const x = dnm.zamanX(nokta.t_utc)
  const y = dnm.fiyatY(nokta.fiyat)
  if (!sayiVarMi(x) || !sayiVarMi(y)) return null
  return { x, y }
}

/**
 * Noktanın A-B DOĞRU PARÇASINA uzaklığı (sonsuz doğruya değil).
 *
 * NEDEN PARÇA: kullanıcı bir trend çizgisini iki ucu arasında çizer. Sonsuz
 * doğru ölçüsü kullanılsaydı, çizginin uzantısı üzerindeki ekranın çok uzak
 * bir köşesine tıklamak da o çizimi seçerdi.
 *
 * Sıfır uzunluklu parça (iki nokta çakışık) bölme hatası verir; o durumda
 * ölçü doğal olarak noktaya uzaklıktır.
 */
export function noktaCizgiyeUzaklik(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): number {
  const dx = bx - ax
  const dy = by - ay
  const uzunlukKare = dx * dx + dy * dy
  if (uzunlukKare === 0) return Math.hypot(px - ax, py - ay)
  const hamOran = ((px - ax) * dx + (py - ay) * dy) / uzunlukKare
  // [0,1] kıstırması parçayı sonsuz doğru olmaktan çıkarır.
  const oran = Math.min(1, Math.max(0, hamOran))
  return Math.hypot(px - (ax + oran * dx), py - (ay + oran * dy))
}

/**
 * Noktanın, köşeleri A ve B olan eksen hizalı dikdörtgene uzaklığı.
 * İÇERİDEKİ nokta için 0 döner: dikdörtgen yarı saydam DOLGUYLA çizilir,
 * dolgunun herhangi bir yerine tıklamak onu seçmelidir.
 * Köşelerin sırası önemsizdir (B, A'nın solunda/üstünde olabilir).
 */
export function noktaDikdortgeneUzaklik(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): number {
  const solX = Math.min(ax, bx)
  const sagX = Math.max(ax, bx)
  const ustY = Math.min(ay, by)
  const altY = Math.max(ay, by)
  const dx = Math.max(solX - px, 0, px - sagX)
  const dy = Math.max(ustY - py, 0, py - altY)
  return Math.hypot(dx, dy)
}

/**
 * Yatay çizgiye uzaklık: SADECE dikey fark.
 * NEDEN x YOK: yatay çizgi panonun tam genişliğinde çizilir, dolayısıyla
 * her x değerinde vardır. x farkını hesaba katmak, çizginin sağ ucundaki
 * tıklamayı "uzak" sayardı.
 */
export function yatayaUzaklik(py: number, cizgiY: number): number {
  return Math.abs(py - cizgiY)
}

/** Dikey çizgiye uzaklık: SADECE yatay fark (aynı gerekçe, tam yükseklik). */
export function dikeyeUzaklik(px: number, cizgiX: number): number {
  return Math.abs(px - cizgiX)
}

/**
 * Bir Fibonacci çiziminin ekrandaki seviye çizgileri.
 * Fib olmayan / noktası eksik çizim için boş dizi döner.
 * Ölçek dışında kalan seviye ATLANIR (uydurulmuş bir y ile çizilmez, Y3).
 */
export function fibCizgileri(cizim: Cizim, dnm: Donusum): FibCizgisi[] {
  if (cizim.tip !== 'fib') return []
  const a = noktaAl(cizim, 0)
  const b = noktaAl(cizim, 1)
  if (a === null || b === null) return []
  const cikti: FibCizgisi[] = []
  for (const seviye of fibSeviyeleri(a, b)) {
    const y = dnm.fiyatY(seviye.fiyat)
    if (!sayiVarMi(y)) continue
    // Sabit 3 hane: oranlar (0.236/0.382/0.618/0.786) üç haneli okunur ve
    // etiketler alt alta aynı genişlikte durur. Yuvarlama YALNIZCA gösterim
    // içindir; `fiyat` alanı ham değeriyle taşınır.
    cikti.push({ oran: seviye.oran, fiyat: seviye.fiyat, y, etiket: seviye.oran.toFixed(3) })
  }
  return cikti
}

/**
 * Ölçüm aracının etiketi: fiyat farkı ve (hesaplanabiliyorsa) yüzde.
 *
 * NEDEN `olcumHesapla` YENİDEN KULLANILIYOR: yüzde kuralı (taban fiyat 0 ya da
 * sonlu değilse `null`) TEK bir yerde tanımlı kalmalıdır; buraya ikinci bir
 * kopyası yazılsaydı biri değişip diğeri eskiyebilirdi. `barSayisi` bu
 * etikette GÖSTERİLMEZ — bu dosya bar dizisini görmez, dolayısıyla bilmediği
 * bir sayıyı arayüze yazamaz (Y3). Çağrıya geçilen 0 yalnızca imzayı
 * doldurur; dönen `barSayisi` alanı OKUNMAZ.
 *
 * Metin tarifseldir (Y8): yalnızca ölçülen fark, yorum yok.
 */
export function olcumEtiketi(a: Nokta, b: Nokta): string {
  const { fiyatFarki, yuzde } = olcumHesapla(a, b, 0)
  // Artı işareti elle eklenir; eksi işaretini toFixed zaten yazar. Yön
  // bilgisi olmadan "12.50" yukarı mı aşağı mı olduğunu göstermez.
  const farkMetni = (fiyatFarki > 0 ? '+' : '') + fiyatFarki.toFixed(2)
  if (yuzde === null) return farkMetni
  return `${farkMetni} (%${yuzde.toFixed(2)})`
}

/**
 * İmlecin çizime uzaklığı (CSS pikseli). Çizim ekrana düşmüyorsa `null`.
 *
 * Her tip KENDİ ölçüsüyle değerlendirilir; hepsini "en yakın uç noktaya
 * uzaklık" gibi tek bir ölçüye indirgemek, uzun bir trend çizgisinin
 * ortasından tıklandığında seçilememesine yol açardı.
 */
export function cizimUzakligi(cizim: Cizim, x: number, y: number, dnm: Donusum): number | null {
  switch (cizim.tip) {
    case 'trend':
    case 'olcum': {
      const a = noktaAl(cizim, 0)
      const b = noktaAl(cizim, 1)
      if (a === null || b === null) return null
      const ea = ekranNoktasi(a, dnm)
      const eb = ekranNoktasi(b, dnm)
      if (ea === null || eb === null) return null
      return noktaCizgiyeUzaklik(x, y, ea.x, ea.y, eb.x, eb.y)
    }

    case 'yatay': {
      // Yatay çizgi için ZAMAN dönüşümü hiç sorulmaz: çizgi tam genişliktedir,
      // tutturulduğu tarih ekranda olmasa bile çizgi ekrandadır. `zamanX`
      // istenseydi, geçmişe kaydırılmış bir tarihe bağlı çizgi seçilemezdi.
      const a = noktaAl(cizim, 0)
      if (a === null) return null
      const cizgiY = dnm.fiyatY(a.fiyat)
      if (!sayiVarMi(cizgiY)) return null
      return yatayaUzaklik(y, cizgiY)
    }

    case 'dikey': {
      // Aynı gerekçenin aynadaki hâli: dikey çizgi için FİYAT sorulmaz.
      const a = noktaAl(cizim, 0)
      if (a === null) return null
      const cizgiX = dnm.zamanX(a.t_utc)
      if (!sayiVarMi(cizgiX)) return null
      return dikeyeUzaklik(x, cizgiX)
    }

    case 'dikdortgen': {
      const a = noktaAl(cizim, 0)
      const b = noktaAl(cizim, 1)
      if (a === null || b === null) return null
      const ea = ekranNoktasi(a, dnm)
      const eb = ekranNoktasi(b, dnm)
      if (ea === null || eb === null) return null
      return noktaDikdortgeneUzaklik(x, y, ea.x, ea.y, eb.x, eb.y)
    }

    case 'fib': {
      // Seviyeler de yatay çizgilerdir; en yakın seviyeye olan dikey fark
      // isabeti belirler. Hiç seviye çizilemiyorsa ortada tıklanacak bir şey
      // yoktur.
      const cizgiler = fibCizgileri(cizim, dnm)
      if (cizgiler.length === 0) return null
      let enAz = Number.POSITIVE_INFINITY
      for (const cizgi of cizgiler) enAz = Math.min(enAz, yatayaUzaklik(y, cizgi.y))
      return enAz
    }

    case 'metin': {
      const a = noktaAl(cizim, 0)
      if (a === null) return null
      const ea = ekranNoktasi(a, dnm)
      if (ea === null) return null
      return Math.hypot(x - ea.x, y - ea.y)
    }

    default: {
      // Yeni bir çizim tipi eklenip burada karşılıksız kalırsa DERLEME hatası
      // verir; çalışma zamanında sessizce "seçilemeyen çizim" olmaz.
      const eksikTip: never = cizim.tip
      void eksikTip
      return null
    }
  }
}

/**
 * Verilen ekran konumuna eşik içinde EN YAKIN çizim.
 *
 * NEDEN BURADA (primitive'de değil): isabet seçimi, kütüphane bağımlı tek
 * satır bile içermeyen saf bir "en küçüğü bul" işidir; `cizim-primitive.ts`'e
 * konsaydı test edilemezdi.
 *
 * Eşitlikte SONRAKİ çizim kazanır: çizimler sırayla boyanır, sonraki üstte
 * görünür; üstte görünen tıklamayı almalıdır.
 */
export function enYakinCizim(
  cizimler: readonly Cizim[],
  x: number,
  y: number,
  dnm: Donusum,
  esik: number = HIT_ESIK_PX,
): { cizim: Cizim; uzaklik: number } | null {
  let sonuc: { cizim: Cizim; uzaklik: number } | null = null
  for (const cizim of cizimler) {
    const uzaklik = cizimUzakligi(cizim, x, y, dnm)
    if (uzaklik === null || uzaklik > esik) continue
    if (sonuc === null || uzaklik <= sonuc.uzaklik) sonuc = { cizim, uzaklik }
  }
  return sonuc
}

/**
 * Seçili çizimin tutamaç konumları — çizimin TUTTURMA noktalarının ekran
 * karşılığı.
 *
 * NEDEN SADECE TUTTURMA NOKTALARI (örn. dikdörtgenin 4 köşesi değil):
 * `cizim-model` reducer'ında nokta bazlı yeniden boyutlandırma eylemi YOKTUR;
 * `TASI` çizimin tamamını taşır. Var olmayan bir etkileşimi ima eden tutamaç
 * çizmek kullanıcıya yalan söylerdi. Bunlar seçimi görünür kılan işaretlerdir.
 *
 * Ekrana düşmeyen nokta ATLANIR: konumu bilinmeyen bir tutamaç çizilemez.
 */
export function tutamacNoktalari(cizim: Cizim, dnm: Donusum): EkranNoktasi[] {
  if (!Array.isArray(cizim.noktalar)) return []
  const cikti: EkranNoktasi[] = []
  for (const nokta of cizim.noktalar) {
    const ekran = ekranNoktasi(nokta, dnm)
    if (ekran !== null) cikti.push(ekran)
  }
  return cikti
}

/**
 * Çizimin boyanabilir biçimi. Ekrana düşmüyorsa (ya da metin çizimi metinsizse)
 * `null` — çağıran taraf onu ATLAR, uydurma bir konuma çizmez (Y3).
 */
export function cizimGorunumu(cizim: Cizim, dnm: Donusum): Gorunum | null {
  switch (cizim.tip) {
    case 'trend':
    case 'olcum': {
      const a = noktaAl(cizim, 0)
      const b = noktaAl(cizim, 1)
      if (a === null || b === null) return null
      const ea = ekranNoktasi(a, dnm)
      const eb = ekranNoktasi(b, dnm)
      if (ea === null || eb === null) return null
      // Etiket YALNIZCA ölçüm aracında vardır; trend çizgisi çıplak kalır.
      const etiket = cizim.tip === 'olcum' ? olcumEtiketi(a, b) : null
      return { tip: 'segment', a: ea, b: eb, etiket }
    }

    case 'yatay': {
      const a = noktaAl(cizim, 0)
      if (a === null) return null
      const y = dnm.fiyatY(a.fiyat)
      if (!sayiVarMi(y)) return null
      return { tip: 'yatay', y }
    }

    case 'dikey': {
      const a = noktaAl(cizim, 0)
      if (a === null) return null
      const x = dnm.zamanX(a.t_utc)
      if (!sayiVarMi(x)) return null
      return { tip: 'dikey', x }
    }

    case 'dikdortgen': {
      const a = noktaAl(cizim, 0)
      const b = noktaAl(cizim, 1)
      if (a === null || b === null) return null
      const ea = ekranNoktasi(a, dnm)
      const eb = ekranNoktasi(b, dnm)
      if (ea === null || eb === null) return null
      return { tip: 'dikdortgen', a: ea, b: eb }
    }

    case 'fib': {
      const cizgiler = fibCizgileri(cizim, dnm)
      if (cizgiler.length === 0) return null
      return { tip: 'fib', cizgiler }
    }

    case 'metin': {
      const a = noktaAl(cizim, 0)
      if (a === null) return null
      const ea = ekranNoktasi(a, dnm)
      if (ea === null) return null
      // Metinsiz bir metin çizimi ekranda görünmez bir nesnedir; boş dize
      // uydurmak yerine hiç çizilmez (şema doğrulaması da bunu reddeder).
      if (typeof cizim.metin !== 'string' || cizim.metin.length === 0) return null
      return { tip: 'metin', nokta: ea, metin: cizim.metin }
    }

    default: {
      const eksikTip: never = cizim.tip
      void eksikTip
      return null
    }
  }
}
