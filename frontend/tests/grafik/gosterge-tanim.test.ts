// Kategori: GRAFİK GÖSTERGE TANIMLARI — tablo değişmezleri, ısınma penceresinin
// gerçekten atlanması, bilinmeyen kimlik davranışı ve Y8 hukuki dil kapısı.
//
// NEDEN BURASI TEST EDİLİYOR: `gosterge-katmani.ts` lightweight-charts'a
// bağımlıdır ve bu depoda DOM/jsdom yoktur, dolayısıyla örneklenemez. Tüm
// KARAR mantığı bilerek `gosterge-tanim.ts`'e taşındı; katmanda karar kalmadı.
// Bu dosya o kararların tamamını sınar.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  GOSTERGE_TANIMLARI,
  gostergeKimlikMi,
  gostergeSerileri,
  seriyiVeriyeCevir,
  tumGostergeKimlikleri,
} from '../../src/lib/grafik/gosterge-tanim'
import type { GostergeKimlik } from '../../src/lib/grafik/gosterge-tanim'

/**
 * Deterministik fiyat serisi: sinüs + eğim. Math.random YOK — testin her
 * koşuda aynı sayıları görmesi gerekiyor.
 */
function seriUret(uzunluk: number): number[] {
  const degerler: number[] = []
  for (let i = 0; i < uzunluk; i++) {
    degerler.push(Math.round((100 + 10 * Math.sin(i / 3) + 0.5 * i) * 100) / 100)
  }
  return degerler
}

/** "YYYY-MM-DD" biçiminde, uzunluğu veriye eşit yapay takvim. */
function zamanUret(uzunluk: number): string[] {
  const zamanlar: string[] = []
  for (let i = 0; i < uzunluk; i++) {
    const gun = new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10)
    zamanlar.push(gun)
  }
  return zamanlar
}

const KAPANISLAR = seriUret(120)

/** Serideki ilk null OLMAYAN indeks; hiç yoksa -1. */
function ilkDoluIndeks(seri: (number | null)[]): number {
  return seri.findIndex((d) => d !== null)
}

test('GOSTERGE_TANIMLARI altı kimliği kapsar ve her kayıt kendi anahtarını taşır', () => {
  const kimlikler = tumGostergeKimlikleri()
  assert.deepEqual(kimlikler, ['sma20', 'sma50', 'ema20', 'bollinger20', 'rsi14', 'macd'])
  for (const kimlik of kimlikler) {
    // Anahtar ile içerideki `kimlik` alanı ayrışırsa arayüz bir göstergeyi
    // seçip başka bir göstergeyi çizerdi; bu sessiz olurdu.
    assert.equal(GOSTERGE_TANIMLARI[kimlik].kimlik, kimlik)
  }
})

test('her tanımda renk sayısı üretilen seri sayısına eşittir', () => {
  for (const kimlik of tumGostergeKimlikleri()) {
    const tanim = GOSTERGE_TANIMLARI[kimlik]
    const uretilen = tanim.hesapla(KAPANISLAR)
    assert.equal(
      tanim.renkler.length,
      uretilen.length,
      `${kimlik}: renk sayısı seri sayısıyla eşleşmiyor`,
    )
    if (tanim.cizimler) {
      assert.equal(tanim.cizimler.length, uretilen.length, `${kimlik}: çizim sayısı uyuşmuyor`)
    }
  }
})

test('her seri girdiyle AYNI uzunlukta döner (indeks hizası korunur)', () => {
  for (const kimlik of tumGostergeKimlikleri()) {
    for (const uretilen of GOSTERGE_TANIMLARI[kimlik].hesapla(KAPANISLAR)) {
      assert.equal(uretilen.seri.length, KAPANISLAR.length, `${kimlik}/${uretilen.ad}`)
    }
  }
})

test('SMA 20 ısınması: ilk 19 indeks null, 19. indeks dolu', () => {
  const seri = GOSTERGE_TANIMLARI.sma20.hesapla(KAPANISLAR)[0].seri
  assert.equal(ilkDoluIndeks(seri), 19)
  for (let i = 0; i < 19; i++) assert.equal(seri[i], null, `indeks ${i} dolu olmamalıydı`)
})

test('SMA 50 ısınması 49. indekste başlar; pencereden kısa seride TAMAMI null', () => {
  const uzun = GOSTERGE_TANIMLARI.sma50.hesapla(KAPANISLAR)[0].seri
  assert.equal(ilkDoluIndeks(uzun), 49)

  const kisa = GOSTERGE_TANIMLARI.sma50.hesapla(seriUret(30))[0].seri
  assert.equal(kisa.length, 30) // uzunluk KORUNUR, kısalmaz
  assert.equal(ilkDoluIndeks(kisa), -1)
})

test('EMA 20 ısınması 19. indekste başlar', () => {
  const seri = GOSTERGE_TANIMLARI.ema20.hesapla(KAPANISLAR)[0].seri
  assert.equal(ilkDoluIndeks(seri), 19)
})

test('Bollinger üç seri üretir, üçü de 19. indekste başlar ve üst >= orta >= alt', () => {
  const uretilen = GOSTERGE_TANIMLARI.bollinger20.hesapla(KAPANISLAR)
  assert.equal(uretilen.length, 3)
  for (const seri of uretilen) assert.equal(ilkDoluIndeks(seri.seri), 19)

  const [ust, orta, alt] = uretilen
  for (let i = 19; i < KAPANISLAR.length; i++) {
    const u = ust.seri[i]
    const o = orta.seri[i]
    const a = alt.seri[i]
    assert.ok(u !== null && o !== null && a !== null, `indeks ${i} boş olmamalıydı`)
    assert.ok((u as number) >= (o as number), `indeks ${i}: üst bant ortanın altında`)
    assert.ok((o as number) >= (a as number), `indeks ${i}: orta bant altın altında`)
  }
})

test('RSI 14 alt panele gider, 14. indekste başlar ve 0-100 aralığında kalır', () => {
  const tanim = GOSTERGE_TANIMLARI.rsi14
  assert.equal(tanim.panel, 'alt')
  const seri = tanim.hesapla(KAPANISLAR)[0].seri
  assert.equal(ilkDoluIndeks(seri), 14)
  for (const deger of seri) {
    if (deger === null) continue
    assert.ok(deger >= 0 && deger <= 100, `RSI aralık dışı: ${deger}`)
  }
})

test('MACD alt panele gider; çizgi 25., sinyal ve histogram 33. indekste başlar', () => {
  const tanim = GOSTERGE_TANIMLARI.macd
  assert.equal(tanim.panel, 'alt')
  const [cizgi, sinyal, histogram] = tanim.hesapla(KAPANISLAR)
  // 25 = yavas(26)-1 ortak tohum noktası; 33 = 25 + sinyal(9)-1.
  assert.equal(ilkDoluIndeks(cizgi.seri), 25)
  assert.equal(ilkDoluIndeks(sinyal.seri), 33)
  assert.equal(ilkDoluIndeks(histogram.seri), 33)
})

test('yalnızca MACD histogramı çubuk çizilir; kalan her seri çizgidir', () => {
  const seriler = gostergeSerileri(tumGostergeKimlikleri(), KAPANISLAR)
  const histogramlar = seriler.filter((s) => s.cizim === 'histogram').map((s) => s.ad)
  assert.deepEqual(histogramlar, ['MACD Histogram'])
})

test('gostergeSerileri: ısınma noktaları seriye TAŞINIR, kırpılmaz', () => {
  const [seri] = gostergeSerileri(['sma20'], KAPANISLAR)
  assert.equal(seri.degerler.length, KAPANISLAR.length)
  assert.equal(seri.degerler[18], null)
  assert.notEqual(seri.degerler[19], null)
  assert.equal(seri.panel, 'ana')
  assert.equal(seri.renk, GOSTERGE_TANIMLARI.sma20.renkler[0])
})

test('gostergeSerileri: boş kimlik listesi boş sonuç verir', () => {
  assert.deepEqual(gostergeSerileri([], KAPANISLAR), [])
})

test('gostergeSerileri: bilinmeyen kimlik boş döner, bilinenle karışınca atlanır', () => {
  assert.deepEqual(gostergeSerileri(['sma99'], KAPANISLAR), [])
  assert.deepEqual(gostergeSerileri(['', 'SMA20', 'toString'], KAPANISLAR), [])

  const karisik = gostergeSerileri(['sma99', 'sma20', 'bilinmeyen'], KAPANISLAR)
  assert.deepEqual(karisik.map((s) => s.ad), ['SMA 20'])
})

test('gostergeSerileri: tekrar eden kimlik seriyi bir kez üretir ve sıra korunur', () => {
  const seriler = gostergeSerileri(['ema20', 'sma20', 'ema20'], KAPANISLAR)
  assert.deepEqual(seriler.map((s) => s.ad), ['EMA 20', 'SMA 20'])
})

test('her seri, üreten göstergenin kimliğini taşır (alt panel gruplaması)', () => {
  const seriler = gostergeSerileri(['bollinger20', 'macd'], KAPANISLAR)
  assert.deepEqual(
    seriler.map((s) => s.kimlik),
    ['bollinger20', 'bollinger20', 'bollinger20', 'macd', 'macd', 'macd'],
  )
  // Alt panel gerektiren KİMLİK sayısı, açılacak panel sayısını belirler.
  const altKimlikler = new Set(
    gostergeSerileri(tumGostergeKimlikleri(), KAPANISLAR)
      .filter((s) => s.panel === 'alt')
      .map((s) => s.kimlik),
  )
  assert.deepEqual([...altKimlikler].sort(), ['macd', 'rsi14'])
})

test('tüm göstergelerin seri adları genelinde BENZERSİZDİR (Map anahtarı)', () => {
  // Katman serileri `ad` ile anahtarlıyor; çakışma bir seriyi görünmez kılardı.
  const adlar = gostergeSerileri(tumGostergeKimlikleri(), KAPANISLAR).map((s) => s.ad)
  assert.equal(new Set(adlar).size, adlar.length, `çakışan ad var: ${adlar.join(', ')}`)
})

test('gostergeSerileri: boş kapanış dizisi patlamaz, değerler boş kalır', () => {
  const seriler = gostergeSerileri(tumGostergeKimlikleri(), [])
  assert.ok(seriler.length > 0)
  for (const seri of seriler) assert.deepEqual(seri.degerler, [])
})

test('hesapla girdi dizisini MUTASYONA UĞRATMAZ', () => {
  const girdi = seriUret(80)
  const kopya = [...girdi]
  gostergeSerileri(tumGostergeKimlikleri(), girdi)
  assert.deepEqual(girdi, kopya)
})

test('gostergeKimlikMi yalnızca tanımlı kimlikler için doğrudur', () => {
  assert.equal(gostergeKimlikMi('rsi14'), true)
  assert.equal(gostergeKimlikMi('rsi15'), false)
  // Object prototip alanları kimlik sanılmamalı (hasOwnProperty kapısı).
  assert.equal(gostergeKimlikMi('constructor'), false)
  assert.equal(gostergeKimlikMi('toString'), false)
})

test('seriyiVeriyeCevir: null noktalar ATLANIR, whitespace bile yazılmaz', () => {
  const zamanlar = zamanUret(5)
  const noktalar = seriyiVeriyeCevir(zamanlar, [null, null, 10, null, 12])
  assert.deepEqual(noktalar, [
    { time: zamanlar[2], value: 10 },
    { time: zamanlar[4], value: 12 },
  ])
})

test('seriyiVeriyeCevir: tamamı null olan seri boş dizi verir', () => {
  assert.deepEqual(seriyiVeriyeCevir(zamanUret(3), [null, null, null]), [])
  assert.deepEqual(seriyiVeriyeCevir([], []), [])
})

test('seriyiVeriyeCevir: NaN ve Infinity noktaları da atlanır (uydurma yok)', () => {
  const zamanlar = zamanUret(4)
  const noktalar = seriyiVeriyeCevir(zamanlar, [Number.NaN, Number.POSITIVE_INFINITY, 7, Number.NEGATIVE_INFINITY])
  assert.deepEqual(noktalar, [{ time: zamanlar[2], value: 7 }])
})

test('seriyiVeriyeCevir: uzunluk uyuşmazlığında yalnızca ortak ön-ek çevrilir', () => {
  const zamanlar = zamanUret(2)
  assert.deepEqual(seriyiVeriyeCevir(zamanlar, [1, 2, 3, 4]), [
    { time: zamanlar[0], value: 1 },
    { time: zamanlar[1], value: 2 },
  ])
  assert.deepEqual(seriyiVeriyeCevir(zamanUret(4), [1, 2]), [
    { time: '2026-01-01', value: 1 },
    { time: '2026-01-02', value: 2 },
  ])
})

test('seriyiVeriyeCevir: sıfır meşru bir değerdir, null sanılıp atlanmaz', () => {
  const zamanlar = zamanUret(2)
  assert.deepEqual(seriyiVeriyeCevir(zamanlar, [0, null]), [{ time: zamanlar[0], value: 0 }])
})

test('gerçek gösterge serisi çevrildiğinde nokta sayısı = ısınma dışı bar sayısı', () => {
  const zamanlar = zamanUret(KAPANISLAR.length)
  const [seri] = gostergeSerileri(['sma20'], KAPANISLAR)
  const noktalar = seriyiVeriyeCevir(zamanlar, seri.degerler)
  assert.equal(noktalar.length, KAPANISLAR.length - 19)
  assert.equal(noktalar[0].time, zamanlar[19])
  assert.equal(noktalar[noktalar.length - 1].time, zamanlar[zamanlar.length - 1])
})

// Y8 HUKUKİ DİL KAPISI — arayüzde görünen HER dizge tarifsel olmak zorunda.
// Kalıplar hukuki_dil.py'deki listeden TÜRETİLDİ (kopyalanmadı); kaynak dosya
// başka bir depodadır ve buradan çağrılamaz.
const YASAKLI_KALIPLAR: { ad: string; kalip: RegExp }[] = [
  { ad: 'emir kipi', kalip: /\w+m[ae]l[iı]s[iı]n[iı]z/i },
  { ad: 'tavsiye', kalip: /tavsiye/i },
  { ad: 'en iyi', kalip: /en iyi/i },
  { ad: 'işlem emri', kalip: /\b(al|sat|gir|yatir|yatır|alin|alın|satin|satın)\b/i },
  { ad: 'kesin kazanç', kalip: /kesin kazan/i },
  { ad: 'risksiz', kalip: /risksiz/i },
  { ad: 'garanti', kalip: /garanti/i },
  { ad: 'fırsat', kalip: /f[iı]rsat/i },
  { ad: 'hedef fiyat', kalip: /hedef fiyat/i },
]

test('Y8: etiketler ve seri adları yasaklı hukuki dil kalıplarını içermez', () => {
  const metinler: string[] = []
  for (const kimlik of tumGostergeKimlikleri()) {
    metinler.push(GOSTERGE_TANIMLARI[kimlik].etiket)
    for (const uretilen of GOSTERGE_TANIMLARI[kimlik].hesapla(KAPANISLAR)) {
      metinler.push(uretilen.ad)
    }
  }
  assert.ok(metinler.length >= 12)
  for (const metin of metinler) {
    for (const { ad, kalip } of YASAKLI_KALIPLAR) {
      assert.equal(kalip.test(metin), false, `"${metin}" metni "${ad}" kalıbına takıldı`)
    }
  }
})

test('Y8 kapısı gerçekten çalışıyor: yasaklı bir metin ELENİR', () => {
  // Kapının kendisi sınanmazsa, hepsi eşleşmeyen bir regex listesi de "geçer".
  const ornekler = ['Bu hisseyi almalısınız', 'risksiz kazanç', 'hedef fiyat 120', 'AL']
  for (const ornek of ornekler) {
    const takildi = YASAKLI_KALIPLAR.some(({ kalip }) => kalip.test(ornek))
    assert.equal(takildi, true, `"${ornek}" yakalanmalıydı`)
  }
})

test('tanımlı kimlik tipi ile tablo anahtarları birbirini tutar', () => {
  // Derleme zamanı kontrolü: tip genişletilip tablo unutulursa burası kırılır.
  const kimlik: GostergeKimlik = 'bollinger20'
  assert.equal(GOSTERGE_TANIMLARI[kimlik].etiket, 'Bollinger (20, 2)')
})
