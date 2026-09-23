// Kategori: GRAFIK / ZAMAN DILIMI - gunluk barlarin haftalik-aylik indirgenmesi.
//
// TUM TESTLER DUSMAN BIR SAAT DILIMINDE kosar. America/New_York'ta UTC gece
// yarisi YEREL olarak bir onceki gundur (2026-03-09 UTC -> yerelde 2026-03-08
// Pazar). Modul yanlislikla getDate()/getDay() kullanirsa barlar bir onceki ISO
// haftasina dusup testler ANINDA patlar. process.env.TZ, modulun kendisi ice
// aktarma aninda hic Date uretmedigi icin burada guvenle ayarlanabilir.
process.env.TZ = 'America/New_York'

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hamBarlariCevir, resample, type Bar } from '../../src/lib/grafik/zaman-dilimi'

/** Test okunakliligi icin kisa bar kurucusu. */
function bar(tarih: string, acilis: number, yuksek: number, dusuk: number, kapanis: number, hacim: number): Bar {
  return { tarih, acilis, yuksek, dusuk, kapanis, hacim }
}

function tarihler(barlar: Bar[]): string[] {
  return barlar.map((b) => b.tarih)
}

test('ORTAM: dusman saat dilimi gercekten etkin (DST testleri sessizce etkisizlesmesin)', () => {
  // Bu dusserse process.env.TZ uygulanmamis demektir ve asagidaki DST testleri
  // hicbir sey kanitlamiyordur - o yuzden ayri ve acik bir kapi olarak duruyor.
  assert.equal(new Date(Date.UTC(2026, 2, 9)).getDate(), 8, 'TZ uygulanmadi: yerel gun UTC ile ayni')
  assert.equal(new Date(Date.UTC(2026, 2, 9)).getUTCDate(), 9)
})

test('CEVIR: canli /price zarfindaki STRING sayilar sayiya cevrilir, hicbiri atlanmaz', () => {
  const ham = {
    ticker: 'AAPL',
    source: 'tiingo',
    count: 2,
    data: [
      { date: '2026-06-16', open: '395.79', close: '393.83', high: '396.84', low: '390.69', volume: '31506846', factor: '1.0' },
      { date: '2026-06-17', open: '393.90', close: '399.10', high: '400.00', low: '392.00', volume: '28000000', factor: '1.0' },
    ],
  }
  const sonuc = hamBarlariCevir(ham)
  assert.equal(sonuc.atlanan, 0)
  assert.deepEqual(sonuc.barlar, [
    bar('2026-06-16', 395.79, 396.84, 390.69, 393.83, 31506846),
    bar('2026-06-17', 393.9, 400, 392, 399.1, 28000000),
  ])
})

test('CEVIR: bozuk/eksik kayitlar ATLANIR ve kac tanesi oldugu geri bildirilir', () => {
  const ham = {
    data: [
      { date: '2026-06-16', open: '10', close: '11', high: '12', low: '9', volume: '100' }, // gecerli
      { date: '2026-06-17', open: '10', close: '11', high: '12', volume: '100' }, // low EKSIK
      { date: '2026-06-18', open: '', close: '11', high: '12', low: '9', volume: '100' }, // bos string (Number('')===0 tuzagi)
      { date: '2026-06-19', open: 'abc', close: '11', high: '12', low: '9', volume: '100' }, // sayisal degil
      { date: '2026-06-22', open: null, close: '11', high: '12', low: '9', volume: '100' }, // null (Number(null)===0 tuzagi)
      { open: '10', close: '11', high: '12', low: '9', volume: '100' }, // tarih YOK
      null, // kayit nesne degil
      'bozuk', // kayit nesne degil
      { date: '2026-06-23', open: '10', close: '11', high: '12', low: '9', volume: '200' }, // gecerli
    ],
  }
  const sonuc = hamBarlariCevir(ham)
  assert.equal(sonuc.barlar.length, 2)
  assert.deepEqual(tarihler(sonuc.barlar), ['2026-06-16', '2026-06-23'])
  assert.equal(sonuc.atlanan, 7, 'atlanan kayit sayisi sessizce yutulmamali')
})

test('CEVIR: gecersiz takvim tarihi ve bozuk tarih bicimi reddedilir (sessiz kayma yok)', () => {
  const bozukTarihler = ['2026-02-30', '2026-13-01', '2026-2-3', '2026-06-16T00:00:00', '0026-01-01', 'abc', '']
  const ham = {
    data: bozukTarihler.map((date) => ({ date, open: '1', close: '1', high: '1', low: '1', volume: '1' })),
  }
  const sonuc = hamBarlariCevir(ham)
  assert.deepEqual(sonuc.barlar, [], 'hicbiri gecerli sayilmamali')
  assert.equal(sonuc.atlanan, bozukTarihler.length)
})

test('CEVIR: zarf tanimsiz/bozuksa cokmez, bos sonuc doner', () => {
  for (const ham of [null, undefined, 42, 'metin', {}, { data: null }, { data: 'dizi degil' }]) {
    const sonuc = hamBarlariCevir(ham)
    assert.deepEqual(sonuc.barlar, [])
    // Hic kayit gelmedigi icin ATLANAN da yoktur: 0 "veri yok", >0 "veri bozuk" demek.
    assert.equal(sonuc.atlanan, 0)
  }
  // Ciplak dizi de kabul edilir (zarfi acilmis yanit).
  const ciplak = hamBarlariCevir([{ date: '2026-06-16', open: '1', close: '2', high: '3', low: '0.5', volume: '7' }])
  assert.equal(ciplak.barlar.length, 1)
  assert.equal(ciplak.atlanan, 0)
})

test('GUNLUK: aynen doner, turetildi=false, eksikSonKova=false ve girdi mutasyona ugramaz', () => {
  const girdi = [bar('2026-06-16', 1, 2, 0.5, 1.5, 10), bar('2026-06-17', 1.5, 3, 1, 2.5, 20)]
  const kopya = girdi.map((b) => ({ ...b }))
  const sonuc = resample(girdi, 'gunluk')
  assert.deepEqual(sonuc.barlar, kopya)
  assert.equal(sonuc.turetildi, false)
  assert.equal(sonuc.eksikSonKova, false)
  assert.notEqual(sonuc.barlar, girdi, 'cikti girdi dizisiyle ayni referans olmamali')
  assert.deepEqual(girdi, kopya, 'girdi degismemeli')
})

test('BOS DIZI: her dilimde cokmez, bos ve bayraklari tutarli doner', () => {
  // `atlanan` alani 23.09.2026'da eklendi (S5): gecersiz tarihli bar sessizce
  // ne gecer ne de sessizce duser - sayisi raporlanir. Bos girdide sifirdir.
  assert.deepEqual(resample([], 'gunluk'), { barlar: [], turetildi: false, eksikSonKova: false, atlanan: 0 })
  assert.deepEqual(resample([], 'haftalik'), { barlar: [], turetildi: true, eksikSonKova: false, atlanan: 0 })
  assert.deepEqual(resample([], 'aylik'), { barlar: [], turetildi: true, eksikSonKova: false, atlanan: 0 })
})

test('TEK BAR: tek elemanli kova aynen tasinir, turetildi=true kalir', () => {
  const sonuc = resample([bar('2026-06-19', 10, 12, 9, 11, 500)], 'haftalik') // 19 Haziran 2026 = Cuma
  assert.equal(sonuc.barlar.length, 1)
  assert.deepEqual(sonuc.barlar[0], bar('2026-06-19', 10, 12, 9, 11, 500))
  assert.equal(sonuc.turetildi, true)
  assert.equal(sonuc.eksikSonKova, false, 'Cuma ile biten hafta kapalidir')
})

test('ISO HAFTA SINIRI: hafta Pazartesi baslar, Pazar ONCEKI haftaya aittir', () => {
  // 2026-01-02 Cuma | 2026-01-03 Cmt | 2026-01-04 Pazar -> hepsi 2025-12-29 haftasi.
  // 2026-01-05 Pazartesi -> YENI hafta.
  const barlar = [
    bar('2026-01-02', 1, 1, 1, 1, 1),
    bar('2026-01-03', 1, 1, 1, 1, 1),
    bar('2026-01-04', 1, 1, 1, 1, 1),
    bar('2026-01-05', 2, 2, 2, 2, 1),
    bar('2026-01-06', 2, 2, 2, 2, 1),
  ]
  const sonuc = resample(barlar, 'haftalik')
  assert.equal(sonuc.barlar.length, 2)
  assert.deepEqual(tarihler(sonuc.barlar), ['2026-01-02', '2026-01-05'])
  assert.equal(sonuc.barlar[0].hacim, 3, 'Cuma+Cmt+Pazar ayni kovada')
  assert.equal(sonuc.barlar[1].hacim, 2)
})

test('YIL SINIRI: 29 Aralik 2025 - 2 Ocak 2026 TEK ISO haftasidir', () => {
  const barlar = [
    bar('2025-12-29', 100, 105, 99, 101, 10), // Pazartesi
    bar('2025-12-30', 101, 106, 100, 102, 10),
    bar('2025-12-31', 102, 107, 101, 103, 10), // Carsamba - yil sonu
    bar('2026-01-01', 103, 108, 102, 104, 10), // Persembe - yil basi
    bar('2026-01-02', 104, 109, 103, 105, 10), // Cuma
    bar('2026-01-05', 200, 201, 199, 200, 50), // sonraki Pazartesi
  ]
  const haftalik = resample(barlar, 'haftalik')
  assert.deepEqual(tarihler(haftalik.barlar), ['2025-12-29', '2026-01-05'])
  assert.equal(haftalik.barlar[0].hacim, 50, 'yil siniri kovayi bolmemeli')
  assert.equal(haftalik.barlar[0].acilis, 100)
  assert.equal(haftalik.barlar[0].kapanis, 105)

  // Ayni veri AYLIK'ta yil sinirinda BOLUNUR (ay = takvim ayi).
  const aylik = resample(barlar, 'aylik')
  assert.deepEqual(tarihler(aylik.barlar), ['2025-12-29', '2026-01-01'])
  assert.equal(aylik.barlar[0].hacim, 30)
  assert.equal(aylik.barlar[1].hacim, 70)
})

test('AY SINIRI: 30-31 Ocak ile 2 Subat ayri aylik kovalara duser', () => {
  const barlar = [
    bar('2026-01-30', 10, 11, 9, 10.5, 100), // Cuma
    bar('2026-01-31', 10.5, 12, 10, 11, 100), // Cumartesi
    bar('2026-02-02', 11, 13, 10.8, 12, 300), // Pazartesi
  ]
  const sonuc = resample(barlar, 'aylik')
  assert.deepEqual(tarihler(sonuc.barlar), ['2026-01-30', '2026-02-02'])
  assert.equal(sonuc.barlar[0].hacim, 200)
  assert.equal(sonuc.barlar[1].hacim, 300)
})

test('BIRLESTIRME: acilis=ilk, yuksek=maks, dusuk=min, kapanis=son', () => {
  const barlar = [
    bar('2026-06-15', 100, 104, 98, 102, 1), // Pazartesi
    bar('2026-06-16', 102, 110, 101, 109, 1), // en yuksek burada
    bar('2026-06-17', 109, 111, 90, 95, 1), // en dusuk burada
    bar('2026-06-18', 95, 99, 94, 97, 1),
    bar('2026-06-19', 97, 103, 96, 101, 1), // Cuma - son
  ]
  const kova = resample(barlar, 'haftalik').barlar[0]
  assert.equal(kova.tarih, '2026-06-15')
  assert.equal(kova.acilis, 100, 'ilk barin acilisi')
  assert.equal(kova.yuksek, 111, 'haftanin maksimumu')
  assert.equal(kova.dusuk, 90, 'haftanin minimumu')
  assert.equal(kova.kapanis, 101, 'son barin kapanisi')
})

test('HACIM: kovadaki hacimler TOPLANIR (ortalama veya son degil)', () => {
  const barlar = [
    bar('2026-06-15', 1, 1, 1, 1, 31506846),
    bar('2026-06-16', 1, 1, 1, 1, 28000000),
    bar('2026-06-17', 1, 1, 1, 1, 12345),
  ]
  const haftalik = resample(barlar, 'haftalik')
  assert.equal(haftalik.barlar[0].hacim, 31506846 + 28000000 + 12345)
  assert.equal(resample(barlar, 'aylik').barlar[0].hacim, 31506846 + 28000000 + 12345)
})

test('EKSIK SON KOVA (haftalik): hafta ortasi acik, Cuma kapali', () => {
  const haftaBasi = [bar('2026-06-15', 1, 1, 1, 1, 1), bar('2026-06-16', 1, 1, 1, 1, 1), bar('2026-06-17', 1, 1, 1, 1, 1)]
  assert.equal(resample(haftaBasi, 'haftalik').eksikSonKova, true, 'Carsamba: Per/Cum hala gelecek')

  const tamHafta = [...haftaBasi, bar('2026-06-18', 1, 1, 1, 1, 1), bar('2026-06-19', 1, 1, 1, 1, 1)]
  assert.equal(resample(tamHafta, 'haftalik').eksikSonKova, false, 'Cuma: haftanin islem gunleri bitti')
})

test('EKSIK SON KOVA (aylik): ay ortasi acik, ay sonu kapali', () => {
  const ayOrtasi = [bar('2026-09-01', 1, 1, 1, 1, 1), bar('2026-09-10', 1, 1, 1, 1, 1)]
  assert.equal(resample(ayOrtasi, 'aylik').eksikSonKova, true)

  const aySonu = [...ayOrtasi, bar('2026-09-30', 1, 1, 1, 1, 1)] // 30 Eylul 2026 = Carsamba, ayin son gunu
  assert.equal(resample(aySonu, 'aylik').eksikSonKova, false)
})

test('EKSIK SON KOVA: ay sonundaki HAFTA SONU gunleri kovayi acik tutmaz', () => {
  // 29 Mayis 2026 Cuma; 30-31 Mayis Cmt/Pazar. Geriye islem gunu kalmadigi icin
  // kova KAPALI sayilmali (takvim gunu kalmasina ragmen).
  const sonuc = resample([bar('2026-05-28', 1, 1, 1, 1, 1), bar('2026-05-29', 1, 1, 1, 1, 1)], 'aylik')
  assert.equal(sonuc.eksikSonKova, false)
})

test('DST MART: ABD (8 Mart) ve AB (29 Mart) gecisleri hafta kovalarini KAYDIRMAZ', () => {
  const barlar = [
    bar('2026-03-05', 1, 1, 1, 1, 1), // Persembe
    bar('2026-03-06', 1, 1, 1, 1, 1), // Cuma  | ABD DST: 8 Mart Pazar
    bar('2026-03-09', 2, 2, 2, 2, 1), // Pazartesi -> YENI hafta
    bar('2026-03-10', 2, 2, 2, 2, 1),
    bar('2026-03-27', 3, 3, 3, 3, 1), // Cuma  | AB DST: 29 Mart Pazar
    bar('2026-03-30', 4, 4, 4, 4, 1), // Pazartesi -> YENI hafta
  ]
  const sonuc = resample(barlar, 'haftalik')
  assert.deepEqual(tarihler(sonuc.barlar), ['2026-03-05', '2026-03-09', '2026-03-27', '2026-03-30'])
  assert.equal(sonuc.barlar[0].hacim, 2)
  assert.equal(sonuc.barlar[1].hacim, 2)
  assert.equal(sonuc.barlar[2].hacim, 1)
  assert.equal(sonuc.barlar[3].hacim, 1)
})

test('DST EKIM/KASIM: AB (25 Ekim) ve ABD (1 Kasim) gecisleri hafta kovalarini KAYDIRMAZ', () => {
  const barlar = [
    bar('2026-10-23', 1, 1, 1, 1, 1), // Cuma | AB DST: 25 Ekim Pazar
    bar('2026-10-26', 2, 2, 2, 2, 1), // Pazartesi -> YENI hafta
    bar('2026-10-30', 2, 2, 2, 2, 1), // Cuma, ayni hafta | ABD DST: 1 Kasim Pazar
    bar('2026-11-02', 3, 3, 3, 3, 1), // Pazartesi -> YENI hafta
  ]
  const sonuc = resample(barlar, 'haftalik')
  assert.deepEqual(tarihler(sonuc.barlar), ['2026-10-23', '2026-10-26', '2026-11-02'])
  assert.equal(sonuc.barlar[1].hacim, 2, '26 ve 30 Ekim ayni ISO haftasinda')
  assert.equal(sonuc.barlar[2].hacim, 1)
})

test('ENTERPOLASYON YOK: tatil/hafta sonu bosluklari doldurulmaz (Y3)', () => {
  // Haftada yalnizca 2 bar var (or. tatil); eksik gunler UYDURULMAZ, kova yine
  // tek bardir ve hacim sadece var olan 2 bari toplar.
  const barlar = [bar('2026-06-15', 10, 12, 9, 11, 100), bar('2026-06-19', 11, 15, 8, 14, 200)]
  const sonuc = resample(barlar, 'haftalik')
  assert.equal(sonuc.barlar.length, 1)
  assert.deepEqual(sonuc.barlar[0], bar('2026-06-15', 10, 15, 8, 14, 300))
  // Aylik tarafta da ay basindaki/ortasindaki bos gunler icin bar uretilmez.
  assert.equal(resample(barlar, 'aylik').barlar.length, 1)
})

test('SAFLIK: sirasiz girdi tarihe gore cozulur ve girdi dizisi degistirilmez', () => {
  const girdi = [
    bar('2026-06-17', 109, 111, 90, 95, 3),
    bar('2026-06-15', 100, 104, 98, 102, 1),
    bar('2026-06-19', 97, 103, 96, 101, 5),
    bar('2026-06-16', 102, 110, 101, 109, 2),
  ]
  const kopya = girdi.map((b) => ({ ...b }))
  const birinci = resample(girdi, 'haftalik')
  assert.deepEqual(birinci.barlar[0], bar('2026-06-15', 100, 111, 90, 101, 11))
  assert.deepEqual(girdi, kopya, 'girdi dizisi mutasyona ugramamali')
  // Ayni girdi -> ayni cikti (determinizm).
  assert.deepEqual(resample(girdi, 'haftalik'), birinci)
})


// =========================================================================
// REGRESYON — 23.09.2026 bağımsız doğrulamasında bulunan S4 ve S5.
// =========================================================================

test('S4 REGRESYON: gunluk yol DERIN kopya doner — cikti mutasyonu girdiyi BOZMAZ', () => {
  // Onceden `barlar.slice()` vardi: dizi kopyalaniyor ama eleman nesneleri
  // PAYLASILIYORDU. Yorum "saflik garantisi" diyordu; iddia yanlisti.
  const girdi = [bar('2026-06-19', 10, 12, 9, 11, 500)]
  const sonuc = resample(girdi, 'gunluk')
  sonuc.barlar[0].kapanis = 999
  assert.equal(girdi[0].kapanis, 11, 'girdi bozuldu — derin kopya degil')
})

test('S4 REGRESYON: haftalik yol da ayni garantiyi verir (yollar tutarli)', () => {
  const girdi = [bar('2026-06-19', 10, 12, 9, 11, 500)]
  const sonuc = resample(girdi, 'haftalik')
  sonuc.barlar[0].kapanis = 999
  assert.equal(girdi[0].kapanis, 11)
})

test('S5 REGRESYON: gecersiz tarihli bar elenir ve SAYISI raporlanir', () => {
  const girdi = [
    bar('bozuk-tarih', 1, 1, 1, 1, 1),
    bar('2026-02-30', 1, 1, 1, 1, 1), // takvimde YOK (Date.UTC sessizce 02 Mart yapar)
    bar('2026-06-19', 10, 12, 9, 11, 500),
  ]
  for (const dilim of ['gunluk', 'haftalik', 'aylik'] as const) {
    const sonuc = resample(girdi, dilim)
    assert.equal(sonuc.atlanan, 2, `${dilim}: 2 bar elenmeliydi`)
    assert.equal(sonuc.barlar.length, 1, `${dilim}: yalnizca gecerli bar kalmali`)
  }
})

test('S5 REGRESYON: eleme HER YOLDA ayni — gunlukte gecip haftalikta dusen bar YOK', () => {
  // S4'te sikayet edilen yollar-arasi tutarsizligin tekrarini engeller.
  const girdi = [bar('2026-13-01', 1, 1, 1, 1, 1), bar('2026-06-19', 10, 12, 9, 11, 500)]
  const gunluk = resample(girdi, 'gunluk')
  const haftalik = resample(girdi, 'haftalik')
  assert.equal(gunluk.atlanan, haftalik.atlanan)
  assert.equal(gunluk.barlar.length, haftalik.barlar.length)
})

test('S5 TERS KONTROL: tamamen gecerli girdide atlanan=0 ve hicbir bar kaybolmaz', () => {
  const girdi = [bar('2026-06-18', 1, 2, 0.5, 1.5, 10), bar('2026-06-19', 10, 12, 9, 11, 500)]
  const sonuc = resample(girdi, 'gunluk')
  assert.equal(sonuc.atlanan, 0)
  assert.equal(sonuc.barlar.length, 2)
  assert.deepEqual(sonuc.barlar, girdi)
})
