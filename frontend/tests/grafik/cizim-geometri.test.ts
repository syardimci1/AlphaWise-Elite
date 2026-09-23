// ÇİZİM GEOMETRİSİ TESTLERİ
//
// Kategoriler: KOORDİNAT ÇEVİRİMİ (üretilemeyen koordinat -> null), DOĞRU
// PARÇASINA UZAKLIK (uç ötesi, sıfır uzunluk), DİKDÖRTGEN, TAM GENİŞLİK/
// YÜKSEKLİK ÇİZGİLERİ, İSABET SEÇİMİ, FİBONACCİ ETİKETLERİ, ÖLÇÜM ETİKETİ,
// GÖRÜNÜM MODELİ ve Y8 (arayüz metninde tavsiye dili yok).
//
// NEDEN GRAFİK KURULMADAN TEST EDİLEBİLİYOR: modül lightweight-charts'ı değil,
// `Donusum` arayüzünü kullanır. Aşağıdaki dönüşümler elle yazılmış ve
// DOĞRUSALDIR (zamanX: t/10, fiyatY: 500-fiyat), böylece beklenen piksel
// değerleri kafadan değil aritmetikle doğrulanabilir.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import type { Cizim, CizimTipi, Nokta } from '../../src/lib/grafik/cizim-model'
import type { Donusum } from '../../src/lib/grafik/cizim-geometri'
import {
  HIT_ESIK_PX,
  cizimGorunumu,
  cizimUzakligi,
  dikeyeUzaklik,
  ekranNoktasi,
  enYakinCizim,
  fibCizgileri,
  noktaCizgiyeUzaklik,
  noktaDikdortgeneUzaklik,
  olcumEtiketi,
  tutamacNoktalari,
  yatayaUzaklik,
} from '../../src/lib/grafik/cizim-geometri'

// --- yardımcılar -------------------------------------------------------------

function nokta(t_utc: number, fiyat: number): Nokta {
  return { t_utc, fiyat }
}

function cizim(id: string, tip: CizimTipi, noktalar: Nokta[], ekstra: Partial<Cizim> = {}): Cizim {
  return {
    v: 1,
    id,
    tip,
    noktalar,
    stil: { renk: '#2962ff', kalinlik: 2 },
    olusturma_utc: 1_757_376_000_000,
    ...ekstra,
  }
}

/** Doğrusal dönüşüm: t=1000 -> x=100, fiyat=100 -> y=400. */
const DNM: Donusum = {
  zamanX: (t_utc) => t_utc / 10,
  fiyatY: (fiyat) => 500 - fiyat,
}

/** Zamanı ekrana düşmeyen dönüşüm (grafikte o tarihte bar yok). */
const DNM_ZAMANSIZ: Donusum = { zamanX: () => null, fiyatY: (fiyat) => 500 - fiyat }

/** Fiyatı ekrana düşmeyen dönüşüm (fiyat ölçeği yok / ölçek dışı). */
const DNM_FIYATSIZ: Donusum = { zamanX: (t_utc) => t_utc / 10, fiyatY: () => null }

/** Kütüphane hatalı bir sayı döndürürse: NaN sessizce yayılmamalı. */
const DNM_NAN: Donusum = { zamanX: () => Number.NaN, fiyatY: () => Number.NaN }

const TREND = cizim('t1', 'trend', [nokta(1000, 100), nokta(3000, 100)])
const YATAY = cizim('y1', 'yatay', [nokta(1000, 100)])
const DIKEY = cizim('d1', 'dikey', [nokta(2000, 100)])
const DIKDORTGEN = cizim('r1', 'dikdortgen', [nokta(1000, 100), nokta(3000, 200)])
const FIB = cizim('f1', 'fib', [nokta(1000, 100), nokta(3000, 200)])
const METIN = cizim('m1', 'metin', [nokta(2000, 150)], { metin: 'not' })
const OLCUM = cizim('o1', 'olcum', [nokta(1000, 100), nokta(3000, 110)])

// --- ekranNoktasi ------------------------------------------------------------

test('ekranNoktasi: doğrusal dönüşümü birebir uygular', () => {
  assert.deepEqual(ekranNoktasi(nokta(1000, 100), DNM), { x: 100, y: 400 })
})

test('ekranNoktasi: zaman ekrana düşmüyorsa null (0 UYDURULMAZ)', () => {
  assert.equal(ekranNoktasi(nokta(1000, 100), DNM_ZAMANSIZ), null)
})

test('ekranNoktasi: fiyat ekrana düşmüyorsa null', () => {
  assert.equal(ekranNoktasi(nokta(1000, 100), DNM_FIYATSIZ), null)
})

test('ekranNoktasi: NaN koordinat kabul edilmez', () => {
  assert.equal(ekranNoktasi(nokta(1000, 100), DNM_NAN), null)
})

// --- noktaCizgiyeUzaklik -----------------------------------------------------

test('noktaCizgiyeUzaklik: parçanın ortasına dik uzaklık', () => {
  // (0,0)-(100,0) parçası, nokta (50,5) -> 5
  assert.equal(noktaCizgiyeUzaklik(50, 5, 0, 0, 100, 0), 5)
})

test('noktaCizgiyeUzaklik: parça üzerindeki nokta 0', () => {
  assert.equal(noktaCizgiyeUzaklik(50, 0, 0, 0, 100, 0), 0)
})

test('noktaCizgiyeUzaklik: A ucunun ötesi, sonsuz doğruya DEĞİL uca ölçülür', () => {
  // Sonsuz doğru ölçüsü 0 verirdi; doğru cevap A'ya uzaklık olan 30'dur.
  assert.equal(noktaCizgiyeUzaklik(-30, 0, 0, 0, 100, 0), 30)
})

test('noktaCizgiyeUzaklik: B ucunun ötesi uca ölçülür', () => {
  assert.equal(noktaCizgiyeUzaklik(140, 0, 0, 0, 100, 0), 40)
})

test('noktaCizgiyeUzaklik: sıfır uzunluklu parça (çakışık noktalar) bölme hatası vermez', () => {
  const uzaklik = noktaCizgiyeUzaklik(3, 4, 0, 0, 0, 0)
  assert.equal(uzaklik, 5)
  assert.equal(Number.isFinite(uzaklik), true)
})

test('noktaCizgiyeUzaklik: eğik parçaya dik uzaklık', () => {
  // (0,0)-(10,10) parçası, nokta (10,0) -> dik ayak (5,5), uzaklık sqrt(50)
  assert.equal(noktaCizgiyeUzaklik(10, 0, 0, 0, 10, 10), Math.hypot(5, 5))
})

// --- dikdörtgen / tam genişlik-yükseklik çizgileri ---------------------------

test('noktaDikdortgeneUzaklik: içerideki nokta 0 (dolgu tıklanabilir)', () => {
  assert.equal(noktaDikdortgeneUzaklik(50, 50, 0, 0, 100, 100), 0)
})

test('noktaDikdortgeneUzaklik: kenar dışı nokta dik uzaklık', () => {
  assert.equal(noktaDikdortgeneUzaklik(50, 110, 0, 0, 100, 100), 10)
})

test('noktaDikdortgeneUzaklik: köşe dışı nokta çapraz uzaklık', () => {
  assert.equal(noktaDikdortgeneUzaklik(103, 104, 0, 0, 100, 100), 5)
})

test('noktaDikdortgeneUzaklik: köşe sırası ters verilse de aynı sonuç', () => {
  assert.equal(
    noktaDikdortgeneUzaklik(103, 104, 100, 100, 0, 0),
    noktaDikdortgeneUzaklik(103, 104, 0, 0, 100, 100),
  )
})

test('yatayaUzaklik / dikeyeUzaklik: mutlak fark, yön bağımsız', () => {
  assert.equal(yatayaUzaklik(405, 400), 5)
  assert.equal(yatayaUzaklik(395, 400), 5)
  assert.equal(dikeyeUzaklik(195, 200), 5)
})

// --- cizimUzakligi -----------------------------------------------------------

test('cizimUzakligi: trend, parçanın ortasından ölçülür', () => {
  // Ekran: (100,400)-(300,400). İmleç (200,405) -> 5
  assert.equal(cizimUzakligi(TREND, 200, 405, DNM), 5)
})

test('cizimUzakligi: olcum, trend ile aynı parça ölçüsünü kullanır', () => {
  // (100,400)-(300,390) parçasının A ucundan 4 piksel aşağısı
  assert.equal(cizimUzakligi(OLCUM, 100, 404, DNM), 4)
})

test('cizimUzakligi: yatay çizgi x ekseninden BAĞIMSIZ (tam genişlikte çizilir)', () => {
  assert.equal(cizimUzakligi(YATAY, 0, 405, DNM), 5)
  assert.equal(cizimUzakligi(YATAY, 99_999, 405, DNM), 5)
})

test('cizimUzakligi: yatay çizgi, tarihi ekranda olmasa da ölçülebilir', () => {
  // zamanX null döner ama yatay çizgi için zaman GEREKMEZ.
  assert.equal(cizimUzakligi(YATAY, 500, 405, DNM_ZAMANSIZ), 5)
})

test('cizimUzakligi: dikey çizgi y ekseninden BAĞIMSIZ ve fiyat gerektirmez', () => {
  assert.equal(cizimUzakligi(DIKEY, 205, 0, DNM), 5)
  assert.equal(cizimUzakligi(DIKEY, 205, 9_999, DNM_FIYATSIZ), 5)
})

test('cizimUzakligi: dikdörtgenin içi 0, dışı gerçek uzaklık', () => {
  // Köşeler (100,400) ve (300,300)
  assert.equal(cizimUzakligi(DIKDORTGEN, 200, 350, DNM), 0)
  assert.equal(cizimUzakligi(DIKDORTGEN, 200, 406, DNM), 6)
})

test('cizimUzakligi: fib, EN YAKIN seviyeye dikey uzaklık', () => {
  // 0.5 seviyesi fiyat 150 -> y 350
  assert.equal(cizimUzakligi(FIB, 0, 353, DNM), 3)
})

test('cizimUzakligi: metin, noktaya öklit uzaklığı', () => {
  // (200,350) noktası; imleç (203,354) -> 5
  assert.equal(cizimUzakligi(METIN, 203, 354, DNM), 5)
})

test('cizimUzakligi: ekrana düşmeyen trend için null döner', () => {
  assert.equal(cizimUzakligi(TREND, 200, 400, DNM_ZAMANSIZ), null)
  assert.equal(cizimUzakligi(TREND, 200, 400, DNM_FIYATSIZ), null)
})

test('cizimUzakligi: eksik noktalı bozuk kayıtta çökmez, null döner', () => {
  const bozuk = cizim('x1', 'trend', [nokta(1000, 100)])
  assert.equal(cizimUzakligi(bozuk, 100, 400, DNM), null)
})

// --- enYakinCizim ------------------------------------------------------------

test('enYakinCizim: eşik içindeki en yakın çizimi uzaklığıyla döndürür', () => {
  const sonuc = enYakinCizim([TREND, YATAY], 200, 402, DNM)
  assert.notEqual(sonuc, null)
  // YATAY y=400'de, TREND de y=400'de: ikisi de 2 piksel uzakta; eşitlikte
  // ÜSTTE çizilen (sonraki) kazanır.
  assert.equal(sonuc?.cizim.id, 'y1')
  assert.equal(sonuc?.uzaklik, 2)
})

test('enYakinCizim: eşik dışındaki hiçbir çizim seçilmez', () => {
  assert.equal(enYakinCizim([TREND], 200, 400 + HIT_ESIK_PX + 1, DNM), null)
  assert.equal(enYakinCizim([TREND], 200, 400 + HIT_ESIK_PX, DNM)?.cizim.id, 't1')
})

test('enYakinCizim: ekrana düşmeyen çizimler atlanır, boş listede null', () => {
  assert.equal(enYakinCizim([TREND], 200, 400, DNM_ZAMANSIZ), null)
  assert.equal(enYakinCizim([], 200, 400, DNM), null)
})

// --- tutamacNoktalari --------------------------------------------------------

test('tutamacNoktalari: tutturma noktalarının ekran karşılığı', () => {
  assert.deepEqual(tutamacNoktalari(TREND, DNM), [
    { x: 100, y: 400 },
    { x: 300, y: 400 },
  ])
})

test('tutamacNoktalari: ekrana düşmeyen nokta atlanır (boş dizi)', () => {
  assert.deepEqual(tutamacNoktalari(TREND, DNM_ZAMANSIZ), [])
})

// --- fibCizgileri ------------------------------------------------------------

test('fibCizgileri: 7 seviye, oran 0 A noktasında ve oran 1 B noktasında', () => {
  const cizgiler = fibCizgileri(FIB, DNM)
  assert.equal(cizgiler.length, 7)
  assert.equal(cizgiler[0].fiyat, 100)
  assert.equal(cizgiler[0].y, 400)
  assert.equal(cizgiler[6].fiyat, 200)
  assert.equal(cizgiler[6].y, 300)
})

test('fibCizgileri: etiketler SADECE sayıdır (Y8 - yorum/tavsiye yok)', () => {
  const etiketler = fibCizgileri(FIB, DNM).map((c) => c.etiket)
  assert.deepEqual(etiketler, ['0.000', '0.236', '0.382', '0.500', '0.618', '0.786', '1.000'])
  for (const etiket of etiketler) assert.match(etiket, /^[0-9]\.[0-9]{3}$/)
})

test('fibCizgileri: fib olmayan tip ve fiyatsız dönüşüm için boş dizi', () => {
  assert.deepEqual(fibCizgileri(TREND, DNM), [])
  assert.deepEqual(fibCizgileri(FIB, DNM_FIYATSIZ), [])
})

// --- olcumEtiketi ------------------------------------------------------------

test('olcumEtiketi: yükseliş farkı artı işaretli, yüzdeyle birlikte', () => {
  assert.equal(olcumEtiketi(nokta(1000, 100), nokta(2000, 110)), '+10.00 (%10.00)')
})

test('olcumEtiketi: düşüş farkı eksi işaretli', () => {
  assert.equal(olcumEtiketi(nokta(1000, 100), nokta(2000, 90)), '-10.00 (%-10.00)')
})

test('olcumEtiketi: taban fiyat 0 ise yüzde HESAPLANAMAZ, etikete yazılmaz', () => {
  const etiket = olcumEtiketi(nokta(1000, 0), nokta(2000, 10))
  assert.equal(etiket, '+10.00')
  assert.equal(etiket.includes('%'), false)
  assert.equal(etiket.includes('Infinity'), false)
  assert.equal(etiket.includes('NaN'), false)
})

// --- cizimGorunumu -----------------------------------------------------------

test('cizimGorunumu: trend segmenti etiketsiz gelir', () => {
  assert.deepEqual(cizimGorunumu(TREND, DNM), {
    tip: 'segment',
    a: { x: 100, y: 400 },
    b: { x: 300, y: 400 },
    etiket: null,
  })
})

test('cizimGorunumu: olcum segmenti fark etiketini taşır', () => {
  const gorunum = cizimGorunumu(OLCUM, DNM)
  assert.equal(gorunum?.tip, 'segment')
  assert.equal(gorunum?.tip === 'segment' ? gorunum.etiket : null, '+10.00 (%10.00)')
})

test('cizimGorunumu: yatay ve dikey yalnızca tek koordinat taşır', () => {
  assert.deepEqual(cizimGorunumu(YATAY, DNM), { tip: 'yatay', y: 400 })
  assert.deepEqual(cizimGorunumu(DIKEY, DNM), { tip: 'dikey', x: 200 })
})

test('cizimGorunumu: dikdörtgen iki köşesiyle gelir', () => {
  assert.deepEqual(cizimGorunumu(DIKDORTGEN, DNM), {
    tip: 'dikdortgen',
    a: { x: 100, y: 400 },
    b: { x: 300, y: 300 },
  })
})

test('cizimGorunumu: metin çizimi metnini taşır, metin yoksa çizilmez', () => {
  assert.deepEqual(cizimGorunumu(METIN, DNM), { tip: 'metin', nokta: { x: 200, y: 350 }, metin: 'not' })
  const metinsiz = cizim('m2', 'metin', [nokta(2000, 150)])
  assert.equal(cizimGorunumu(metinsiz, DNM), null)
})

test('cizimGorunumu: ekrana düşmeyen her tip için null', () => {
  for (const c of [TREND, YATAY, DIKDORTGEN, FIB, METIN, OLCUM]) {
    assert.equal(cizimGorunumu(c, DNM_FIYATSIZ), null, `${c.tip} fiyatsız dönüşümde null olmalı`)
  }
  assert.equal(cizimGorunumu(DIKEY, DNM_ZAMANSIZ), null)
})

test('Y8: üretilen tüm arayüz metinleri tarifseldir (emir/tavsiye kipi yok)', () => {
  const metinler = [
    ...fibCizgileri(FIB, DNM).map((c) => c.etiket),
    olcumEtiketi(nokta(1000, 100), nokta(2000, 110)),
    olcumEtiketi(nokta(1000, 100), nokta(2000, 90)),
  ]
  // Yasaklı kalıplar: emir kipi, tavsiye, üstünlük, kesinlik iddiası.
  const yasakli = [
    /\w+m[ae]l[iı]s[iı]n[iı]z/i,
    /tavsiye/i,
    /en iyi/i,
    /\b(al|sat|gir|yatır)\b/i,
    /kesin kazanç/i,
    /risksiz/i,
    /garanti/i,
    /hedef/i,
    /fırsat/i,
  ]
  for (const metin of metinler) {
    for (const kalip of yasakli) {
      assert.equal(kalip.test(metin), false, `"${metin}" yasaklı kalıp içeriyor: ${kalip}`)
    }
  }
})
