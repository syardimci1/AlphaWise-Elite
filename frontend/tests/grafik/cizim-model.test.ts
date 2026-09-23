// Kategoriler: ŞEMA DOĞRULAMA (nokta sayısı, sürüm), MUTASYONSUZLUK
// (girdi donduruluyor), GERİ AL/YİNELE SIRASI (LIFO), İLERİ YIĞINININ
// TEMİZLENMESİ, ÖLÇÜM (sıfıra bölme → null), FİBONACCİ SEVİYELERİ.
//
// NEDEN DONDURARAK TEST: ESM modülleri katı kipte (strict mode) çalışır;
// donmuş bir nesneye yazmak sessizce yutulmaz, TypeError fırlatır. Yani
// "reducer girdiyi değiştirmiyor" iddiası sadece anlık görüntü
// karşılaştırmasıyla değil, çalışma zamanında da zorlanır.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import type { Cizim, CizimTipi, Durum, Nokta } from '../../src/lib/grafik/cizim-model'
import {
  reducer,
  bosDurum,
  gecerliCizim,
  olcumHesapla,
  fibSeviyeleri,
  FIB_SEVIYELERI,
  GEREKLI_NOKTA_SAYISI,
} from '../../src/lib/grafik/cizim-model'

// --- yardımcılar (deterministik: Date.now/Math.random YOK) -------------------

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
    olusturma_utc: 1_757_376_000_000, // 2025-09-09T00:00:00Z — sabit damga
    ...ekstra,
  }
}

const TREND = cizim('c1', 'trend', [nokta(1000, 100), nokta(2000, 120)])
const YATAY = cizim('c2', 'yatay', [nokta(1500, 110)])

/** Nesneyi ve içindeki tüm dizileri/nesneleri özyinelemeli dondurur. */
function derinDondur<T>(deger: T): T {
  if (deger !== null && typeof deger === 'object') {
    for (const alt of Object.values(deger as Record<string, unknown>)) derinDondur(alt)
    Object.freeze(deger)
  }
  return deger
}

/** Yapısal anlık görüntü: referans değil, İÇERİK karşılaştırması için. */
function anlikGoruntu(deger: unknown): string {
  return JSON.stringify(deger)
}

function durumOlustur(cizimler: Cizim[]): Durum {
  return cizimler.reduce((d, c) => reducer(d, { tip: 'EKLE', cizim: c }), bosDurum())
}

// --- EKLE -------------------------------------------------------------------

test('EKLE: geçerli çizim eklenir, seçili olur, geri yığını büyür, ileri boş kalır', () => {
  const sonra = reducer(bosDurum(), { tip: 'EKLE', cizim: TREND })
  assert.deepEqual(sonra.cizimler, [TREND])
  assert.equal(sonra.seciliId, 'c1')
  assert.equal(sonra.geri.length, 1)
  assert.deepEqual(sonra.geri[0], []) // eklemeden önceki hâl
  assert.equal(sonra.ileri.length, 0)
})

test('MUTASYONSUZLUK: donmuş girdi durumu EKLE/TASI/SIL ile değişmez', () => {
  const once = derinDondur(durumOlustur([TREND, YATAY]))
  const kopya = anlikGoruntu(once)

  const eklendi = reducer(once, { tip: 'EKLE', cizim: cizim('c3', 'dikey', [nokta(3000, 0)]) })
  const tasindi = reducer(once, { tip: 'TASI', id: 'c1', dx_t: 10, dy_fiyat: 1 })
  const silindi = reducer(once, { tip: 'SIL', id: 'c2' })

  assert.equal(anlikGoruntu(once), kopya, 'girdi durumu değişmemeli')
  assert.notEqual(eklendi, once)
  assert.notEqual(tasindi, once)
  assert.notEqual(silindi, once)
  // Taşınan çizimin ESKİ nesnesi de bozulmamalı (derin kopya, yerinde değil).
  assert.deepEqual(once.cizimler[0].noktalar, [nokta(1000, 100), nokta(2000, 120)])
})

test('ŞEMA: eksik/fazla nokta sayısı → eylem yok sayılır, durum referansı AYNI kalır', () => {
  const baslangic = bosDurum()
  const eksikTrend = cizim('x1', 'trend', [nokta(1000, 100)]) // 2 gerekirken 1
  const fazlaYatay = cizim('x2', 'yatay', [nokta(1000, 100), nokta(2000, 120)]) // 1 gerekirken 2
  const bosMetin = cizim('x3', 'metin', [], { metin: 'not' }) // 1 gerekirken 0

  for (const bozuk of [eksikTrend, fazlaYatay, bosMetin]) {
    const sonra = reducer(baslangic, { tip: 'EKLE', cizim: bozuk })
    assert.equal(sonra, baslangic, `${bozuk.tip} için durum değişmemeli`)
  }
})

test('ŞEMA: tüm tiplerin gerekli nokta sayısı sözleşmeye uyar', () => {
  assert.deepEqual(GEREKLI_NOKTA_SAYISI, {
    trend: 2, yatay: 1, dikey: 1, dikdortgen: 2, fib: 2, metin: 1, olcum: 2,
  })
  assert.equal(gecerliCizim(cizim('a', 'dikdortgen', [nokta(1, 1), nokta(2, 2)])), true)
  assert.equal(gecerliCizim(cizim('a', 'olcum', [nokta(1, 1)])), false)
  assert.equal(gecerliCizim(cizim('a', 'fib', [nokta(1, 1), nokta(2, 2), nokta(3, 3)])), false)
  // NaN/Infinity taşıyan nokta reddedilir (Y3: sessizce zehirlenmiş ölçüm yok).
  assert.equal(gecerliCizim(cizim('a', 'yatay', [nokta(1, Number.NaN)])), false)
  assert.equal(gecerliCizim(cizim('a', 'yatay', [nokta(Number.POSITIVE_INFINITY, 5)])), false)
  assert.equal(gecerliCizim(cizim('', 'yatay', [nokta(1, 1)])), false) // boş kimlik
})

test('ŞEMA/SÜRÜM: v !== 1 olan çizim eklenmez (eski kayıt sessizce yorumlanmaz)', () => {
  const eskiSurum = { ...TREND, v: 2 } as unknown as Cizim
  const baslangic = bosDurum()
  assert.equal(reducer(baslangic, { tip: 'EKLE', cizim: eskiSurum }), baslangic)
  assert.equal(gecerliCizim(eskiSurum), false)
})

test('EKLE: aynı kimlik ikinci kez eklenemez (SIL/TASI hedefi belirsizleşmesin)', () => {
  const durum = durumOlustur([TREND])
  const tekrar = reducer(durum, { tip: 'EKLE', cizim: cizim('c1', 'yatay', [nokta(9, 9)]) })
  assert.equal(tekrar, durum)
  assert.equal(durum.cizimler.length, 1)
})

// --- SEC --------------------------------------------------------------------

test('SEC: var olan kimlik seçilir, null ile seçim kalkar, geçmiş KİRLENMEZ', () => {
  const durum = durumOlustur([TREND, YATAY])
  const geriDerinlik = durum.geri.length

  const secili = reducer(durum, { tip: 'SEC', id: 'c1' })
  assert.equal(secili.seciliId, 'c1')
  assert.equal(secili.geri.length, geriDerinlik, 'seçim belgeyi değiştirmez')
  assert.deepEqual(secili.ileri, [])

  const bosaltilmis = reducer(secili, { tip: 'SEC', id: null })
  assert.equal(bosaltilmis.seciliId, null)
})

test('SEC: olmayan kimlik yok sayılır; aynı kimliğin tekrarı yeni nesne üretmez', () => {
  const durum = durumOlustur([TREND])
  assert.equal(reducer(durum, { tip: 'SEC', id: 'yok-boyle-bir-id' }), durum)
  assert.equal(reducer(durum, { tip: 'SEC', id: 'c1' }), durum) // zaten seçili
})

// --- TASI -------------------------------------------------------------------

test('TASI: tüm noktalar dx_t/dy_fiyat kadar kayar, diğer çizimler dokunulmaz', () => {
  const durum = durumOlustur([TREND, YATAY])
  const sonra = reducer(durum, { tip: 'TASI', id: 'c1', dx_t: 500, dy_fiyat: -10 })
  assert.deepEqual(sonra.cizimler[0].noktalar, [nokta(1500, 90), nokta(2500, 110)])
  assert.equal(sonra.cizimler[0].id, 'c1')
  assert.equal(sonra.cizimler[0].tip, 'trend')
  assert.deepEqual(sonra.cizimler[1], YATAY) // komşu çizim aynen kalır
  assert.equal(sonra.geri.length, durum.geri.length + 1)
})

test('TASI: olmayan kimlik ve sıfır kayma yok sayılır (geçmiş kirlenmez)', () => {
  const durum = durumOlustur([TREND])
  assert.equal(reducer(durum, { tip: 'TASI', id: 'yok', dx_t: 5, dy_fiyat: 5 }), durum)
  assert.equal(reducer(durum, { tip: 'TASI', id: 'c1', dx_t: 0, dy_fiyat: 0 }), durum)
})

// --- SIL / TEMIZLE ----------------------------------------------------------

test('SIL: çizim listeden çıkar, seçiliyse seçim düşer; olmayan kimlik yok sayılır', () => {
  const durum = durumOlustur([TREND, YATAY]) // son eklenen (c2) seçili
  assert.equal(durum.seciliId, 'c2')

  const sonra = reducer(durum, { tip: 'SIL', id: 'c2' })
  assert.deepEqual(sonra.cizimler.map((c) => c.id), ['c1'])
  assert.equal(sonra.seciliId, null)

  assert.equal(reducer(sonra, { tip: 'SIL', id: 'c2' }), sonra) // artık yok
})

test('SIL: seçili OLMAYAN çizim silinince seçim korunur', () => {
  const durum = durumOlustur([TREND, YATAY]) // c2 seçili
  const sonra = reducer(durum, { tip: 'SIL', id: 'c1' })
  assert.equal(sonra.seciliId, 'c2')
})

test('TEMIZLE: hepsi silinir ama GERI_AL ile tamamen geri gelir; boşta yok sayılır', () => {
  const durum = durumOlustur([TREND, YATAY])
  const temiz = reducer(durum, { tip: 'TEMIZLE' })
  assert.deepEqual(temiz.cizimler, [])
  assert.equal(temiz.seciliId, null)

  const geriAlindi = reducer(temiz, { tip: 'GERI_AL' })
  assert.deepEqual(geriAlindi.cizimler.map((c) => c.id), ['c1', 'c2'])

  assert.equal(reducer(bosDurum(), { tip: 'TEMIZLE' }).cizimler.length, 0)
  const bos = bosDurum()
  assert.equal(reducer(bos, { tip: 'TEMIZLE' }), bos)
})

// --- GERI_AL / YINELE -------------------------------------------------------

test('GERI_AL/YINELE: LIFO sırası korunur (3 ekleme → 2 geri → 2 yinele)', () => {
  const ucuncu = cizim('c3', 'dikey', [nokta(3000, 0)])
  const d3 = durumOlustur([TREND, YATAY, ucuncu])
  assert.deepEqual(d3.cizimler.map((c) => c.id), ['c1', 'c2', 'c3'])

  const g1 = reducer(d3, { tip: 'GERI_AL' })
  assert.deepEqual(g1.cizimler.map((c) => c.id), ['c1', 'c2'])
  const g2 = reducer(g1, { tip: 'GERI_AL' })
  assert.deepEqual(g2.cizimler.map((c) => c.id), ['c1'])

  const y1 = reducer(g2, { tip: 'YINELE' })
  assert.deepEqual(y1.cizimler.map((c) => c.id), ['c1', 'c2'])
  const y2 = reducer(y1, { tip: 'YINELE' })
  assert.deepEqual(y2.cizimler.map((c) => c.id), ['c1', 'c2', 'c3'])
  assert.equal(y2.ileri.length, 0)
  assert.deepEqual(anlikGoruntu(y2.cizimler), anlikGoruntu(d3.cizimler))
})

test('GERI_AL/YINELE: boş yığınlarda durum referansı değişmez', () => {
  const bos = bosDurum()
  assert.equal(reducer(bos, { tip: 'GERI_AL' }), bos)
  assert.equal(reducer(bos, { tip: 'YINELE' }), bos)

  const durum = durumOlustur([TREND])
  assert.equal(reducer(durum, { tip: 'YINELE' }), durum) // hiç geri alınmadı
})

test('GERI_AL: geçmişte artık bulunmayan seçili çizim için seçim null olur', () => {
  const durum = durumOlustur([TREND, YATAY]) // c2 seçili
  const geriAlindi = reducer(durum, { tip: 'GERI_AL' }) // c2 yok oldu
  assert.deepEqual(geriAlindi.cizimler.map((c) => c.id), ['c1'])
  assert.equal(geriAlindi.seciliId, null)
})

test('İLERİ YIĞINI: geri al sonrası yeni bir değişiklik yinele geçmişini TEMİZLER', () => {
  const durum = durumOlustur([TREND, YATAY])
  const geriAlindi = reducer(durum, { tip: 'GERI_AL' })
  assert.equal(geriAlindi.ileri.length, 1)

  const yeniDal = reducer(geriAlindi, { tip: 'EKLE', cizim: cizim('c9', 'fib', [nokta(1, 10), nokta(2, 20)]) })
  assert.equal(yeniDal.ileri.length, 0, 'ulaşılamayan dal tutulmamalı')
  assert.equal(reducer(yeniDal, { tip: 'YINELE' }), yeniDal)
})

// --- YUKLE ------------------------------------------------------------------

test('YUKLE: geçerli liste yüklenir, seçim düşer ve geçmiş sıfırlanır', () => {
  const onceki = durumOlustur([TREND, YATAY])
  const yuklenen = reducer(onceki, { tip: 'YUKLE', cizimler: [cizim('k1', 'olcum', [nokta(10, 1), nokta(20, 2)])] })
  assert.deepEqual(yuklenen.cizimler.map((c) => c.id), ['k1'])
  assert.equal(yuklenen.seciliId, null)
  assert.deepEqual(yuklenen.geri, [])
  assert.deepEqual(yuklenen.ileri, [])
})

test('YUKLE: tek bozuk kayıt tüm yüklemeyi reddeder (kısmi yükleme YOK)', () => {
  const durum = durumOlustur([TREND])
  const bozukListe = [cizim('k1', 'yatay', [nokta(10, 1)]), cizim('k2', 'trend', [nokta(20, 2)])]
  assert.equal(reducer(durum, { tip: 'YUKLE', cizimler: bozukListe }), durum)

  // Yinelenen kimlik de reddedilir.
  const cift = [cizim('ayni', 'yatay', [nokta(1, 1)]), cizim('ayni', 'dikey', [nokta(2, 2)])]
  assert.equal(reducer(durum, { tip: 'YUKLE', cizimler: cift }), durum)
})

// --- OLCUM ------------------------------------------------------------------

test('OLCUM: fiyat farkı, yüzde ve bar sayısı doğru; yön işareti korunur', () => {
  const yukselis = olcumHesapla(nokta(1000, 100), nokta(2000, 125), 17)
  assert.equal(yukselis.fiyatFarki, 25)
  assert.equal(yukselis.yuzde, 25)
  assert.equal(yukselis.barSayisi, 17)

  const dusus = olcumHesapla(nokta(1000, 200), nokta(2000, 150), 4)
  assert.equal(dusus.fiyatFarki, -50)
  assert.equal(dusus.yuzde, -25)
})

test('OLCUM: başlangıç fiyatı 0 ise yüzde null (sıfıra bölme uydurulmaz)', () => {
  const olcum = olcumHesapla(nokta(1000, 0), nokta(2000, 50), 3)
  assert.equal(olcum.yuzde, null)
  assert.equal(olcum.fiyatFarki, 50) // fark yine de hesaplanabilir
  assert.equal(olcum.barSayisi, 3)
  assert.equal(olcumHesapla(nokta(1, Number.NaN), nokta(2, 5), 1).yuzde, null)
})

// --- FIBONACCI --------------------------------------------------------------

test('FIB: 7 seviye; 0 → a.fiyat, 1 → b.fiyat, 0.5 → tam orta', () => {
  const seviyeler = fibSeviyeleri(nokta(1000, 100), nokta(2000, 200))
  assert.equal(seviyeler.length, FIB_SEVIYELERI.length)
  assert.equal(seviyeler.length, 7)
  assert.deepEqual(seviyeler.map((s) => s.oran), [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1])
  assert.equal(seviyeler[0].fiyat, 100)
  assert.equal(seviyeler[6].fiyat, 200)
  assert.equal(seviyeler[3].fiyat, 150)
  assert.ok(Math.abs(seviyeler[4].fiyat - 161.8) < 1e-9)
})

test('FIB: düşüş yönünde (a > b) seviyeler yönü koruyarak azalır', () => {
  const seviyeler = fibSeviyeleri(nokta(1000, 200), nokta(2000, 100))
  assert.equal(seviyeler[0].fiyat, 200)
  assert.equal(seviyeler[6].fiyat, 100)
  assert.equal(seviyeler[3].fiyat, 150)
  for (let i = 1; i < seviyeler.length; i++) {
    assert.ok(seviyeler[i].fiyat < seviyeler[i - 1].fiyat, 'seviyeler monoton azalmalı')
  }
})

// --- SAFLIK -----------------------------------------------------------------

test('SAFLIK: aynı girdi → aynı çıktı (rastgelelik/saat yan etkisi yok)', () => {
  const durum = durumOlustur([TREND, YATAY])
  const a = reducer(durum, { tip: 'TASI', id: 'c1', dx_t: 7, dy_fiyat: 0.5 })
  const b = reducer(durum, { tip: 'TASI', id: 'c1', dx_t: 7, dy_fiyat: 0.5 })
  assert.deepEqual(a, b)
  assert.equal(anlikGoruntu(a), anlikGoruntu(b))
  assert.deepEqual(bosDurum(), bosDurum())
  assert.notEqual(bosDurum(), bosDurum(), 'her çağrı taze nesne döndürmeli')
})

// =========================================================================
// REGRESYON — 23.09.2026 bağımsız doğrulamasında bulunan S1 ve S2 hataları.
//
// Bu blok, `gecerliCizim`'in GÜVENİLMEYEN GİRDİ SINIRI olduğunu kilitler:
// veri localStorage'dan gelir; kullanıcı elle düzenleyebilir, eski bir sürüm
// veya başka bir sekme yazmış olabilir. Sözleşme "çökme yok, false dön"dür.
// Bu testlerin hepsi düzeltmeden ÖNCE ya fırlatıyordu (S1) ya da yanlışlıkla
// `true` dönüyordu (S2).
// =========================================================================

/** Bozuk kayıtları yazabilmek için: `any` DEĞİL (Y13), `unknown` üzerinden. */
function bozuk(deger: unknown): Cizim {
  return deger as unknown as Cizim
}

const GECERLI_STIL = { renk: '#2962ff', kalinlik: 2 }

function ham(ustuneYaz: Record<string, unknown> = {}): Cizim {
  return bozuk({
    v: 1,
    id: 'x1',
    tip: 'trend',
    noktalar: [{ t_utc: 1000, fiyat: 100 }, { t_utc: 2000, fiyat: 120 }],
    stil: GECERLI_STIL,
    olusturma_utc: 1_700_000_000_000,
    ...ustuneYaz,
  })
}

test('S1 REGRESYON: noktalar dizisinin ELEMANI null ise ÇÖKMEZ, false döner', () => {
  // JSON'da eksik/bozuk bir nesnenin doğal gösterimi `null`'dır ve
  // `typeof null === "object"` olduğu için bu vaka kolayca gözden kaçar.
  assert.doesNotThrow(() => gecerliCizim(ham({ noktalar: [null, null] })))
  assert.equal(gecerliCizim(ham({ noktalar: [null, null] })), false)
})

test('S1 REGRESYON: nokta yerine geçen her ilkel tip ÇÖKMEDEN reddedilir', () => {
  for (const kotu of [null, undefined, 42, 'nokta', true, []]) {
    const c = ham({ noktalar: [kotu, { t_utc: 2000, fiyat: 120 }] })
    assert.doesNotThrow(() => gecerliCizim(c), `${String(kotu)} fırlattı`)
    assert.equal(gecerliCizim(c), false, `${String(kotu)} reddedilmeliydi`)
  }
})

test('S1 REGRESYON: reducer YUKLE eylemi de bozuk noktalarda ÇÖKMEZ', () => {
  // gecerliCizim düzeltilse bile reducer onu çağırmasaydı çökme sürerdi;
  // bu test saf fonksiyon ile reducer arasındaki BAĞI kilitler.
  const baslangic = bosDurum()
  const eylem = { tip: 'YUKLE' as const, cizimler: [ham({ noktalar: [null, null] })] }
  assert.doesNotThrow(() => reducer(baslangic, eylem))
  // Bozuk liste sessizce YÜKLENMEZ: durum değişmeden kalır.
  assert.deepEqual(reducer(baslangic, eylem).cizimler, [])
})

test('S2 REGRESYON: stil eksik/bozuksa YÜKLEME anında reddedilir (çizim anında değil)', () => {
  assert.equal(gecerliCizim(ham({ stil: undefined })), false, 'stil yok')
  assert.equal(gecerliCizim(ham({ stil: null })), false, 'stil null')
  assert.equal(gecerliCizim(ham({ stil: 'mavi' })), false, 'stil dize')
  assert.equal(gecerliCizim(ham({ stil: { kalinlik: 2 } })), false, 'renk yok')
  assert.equal(gecerliCizim(ham({ stil: { renk: '', kalinlik: 2 } })), false, 'renk boş')
  assert.equal(gecerliCizim(ham({ stil: { renk: '#fff' } })), false, 'kalınlık yok')
  assert.equal(gecerliCizim(ham({ stil: { renk: '#fff', kalinlik: 0 } })), false, 'kalınlık 0')
  assert.equal(gecerliCizim(ham({ stil: { renk: '#fff', kalinlik: -1 } })), false, 'kalınlık negatif')
  assert.equal(gecerliCizim(ham({ stil: { renk: '#fff', kalinlik: NaN } })), false, 'kalınlık NaN')
})

test('S2 REGRESYON: olusturma_utc sonlu bir sayı olmalı', () => {
  assert.equal(gecerliCizim(ham({ olusturma_utc: undefined })), false)
  assert.equal(gecerliCizim(ham({ olusturma_utc: 'dun' })), false)
  assert.equal(gecerliCizim(ham({ olusturma_utc: NaN })), false)
  assert.equal(gecerliCizim(ham({ olusturma_utc: Infinity })), false)
})

test('S2 REGRESYON: metin alanı — varsa dize, "metin" tipinde ZORUNLU', () => {
  assert.equal(gecerliCizim(ham({ metin: 123 })), false, 'metin sayı olamaz')
  assert.equal(gecerliCizim(ham({ metin: 'not' })), true, 'geçerli metin kabul edilir')
  const metinCizimi = (m: unknown) =>
    ham({ tip: 'metin', noktalar: [{ t_utc: 1000, fiyat: 100 }], metin: m })
  assert.equal(gecerliCizim(metinCizimi(undefined)), false, 'metin tipi metinsiz olamaz')
  assert.equal(gecerliCizim(metinCizimi('etiket')), true)
})

test('TERS KONTROL: sıkılaştırma tamamen geçerli bir çizimi reddetmiyor', () => {
  // S1/S2 düzeltmesi aşırıya kaçsaydı bu test kırmızıya dönerdi.
  assert.equal(gecerliCizim(ham()), true)
  assert.equal(gecerliCizim(TREND), true)
  assert.equal(gecerliCizim(YATAY), true)
})

test('B2 REGRESYON: boş metinli "metin" çizimi şemadan GEÇMEZ (görünmez hayalet)', () => {
  // Bulgu: boş dize şemadan geçiyordu. Sonuç bir hayalet nesneydi —
  // `cizimGorunumu` boş metinde null döndüğü için ÇİZİLMİYOR, ama
  // `cizimUzakligi` metni hiç sormadığı için hit-test onu BULUYORDU.
  // Yani kullanıcı görmediği bir şeyi seçebiliyordu.
  const metinCizimi = (m: unknown) =>
    ham({ tip: 'metin', noktalar: [{ t_utc: 1000, fiyat: 100 }], metin: m })
  assert.equal(gecerliCizim(metinCizimi('')), false, 'boş dize')
  assert.equal(gecerliCizim(metinCizimi('   ')), false, 'yalnızca boşluk')
  assert.equal(gecerliCizim(metinCizimi('\t\n')), false, 'yalnızca sekme/satırsonu')
  assert.equal(gecerliCizim(metinCizimi('not')), true, 'gerçek metin hâlâ geçer')
  assert.equal(gecerliCizim(metinCizimi(' not ')), true, 'kenar boşluklu metin geçer')
})

test('B2 REGRESYON: reducer boş metinli çizimi EKLEMEZ', () => {
  const baslangic = bosDurum()
  const bos = ham({ tip: 'metin', noktalar: [{ t_utc: 1000, fiyat: 100 }], metin: '' })
  assert.deepEqual(reducer(baslangic, { tip: 'EKLE', cizim: bos }).cizimler, [])
})
