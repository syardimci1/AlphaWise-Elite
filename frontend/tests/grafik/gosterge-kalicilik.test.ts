// Kategori: KALICILIK (ADR-5) - gosterge secimi localStorage ad alani, surum gocu, fail-loud hata.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  gostergeAnahtari,
  gostergeleriKaydet,
  gostergeleriYukle,
  gostergeleriSil,
} from '../../src/lib/grafik/gosterge-kalicilik'
import { anahtarUret, type Depo } from '../../src/lib/grafik/cizim-kalicilik'

/** Bellek ici sahte depo - gercek localStorage semantigi (yoksa null doner). */
class BellekDepo implements Depo {
  readonly kutu = new Map<string, string>()
  yazimSayisi = 0
  getItem(anahtar: string): string | null {
    const deger = this.kutu.get(anahtar)
    return deger === undefined ? null : deger
  }
  setItem(anahtar: string, deger: string): void {
    this.yazimSayisi += 1
    this.kutu.set(anahtar, deger)
  }
  removeItem(anahtar: string): void {
    this.kutu.delete(anahtar)
  }
}

const ZAMAN = 1758700000000

// ---------------------------------------------------------------- S1: temel tur

test('GOSTERGE KALICILIK: anahtar bicimi cizimle ayni desende, tur ayri', () => {
  assert.equal(gostergeAnahtari('kullanici-7', 'aapl'), 'alphawise:grafik:gosterge:v1:kullanici-7:AAPL')
  // Ayni kullanici + sembol icin gosterge ve cizim AYRI anahtarlardir (C2).
  assert.notEqual(gostergeAnahtari('ali', 'AAPL'), anahtarUret('ali', 'AAPL'))
})

test('GOSTERGE KALICILIK: kimlik ve sembol kacislanir - ad alani cakismasi YOK', () => {
  assert.notEqual(gostergeAnahtari('a', 'B:C'), gostergeAnahtari('a:B', 'C'))
  assert.equal(gostergeAnahtari('ali', 'isctr'), 'alphawise:grafik:gosterge:v1:ali:ISCTR')
})

test('GOSTERGE KALICILIK: kaydet/yukle gidis-donusu kayipsiz, uyari yok, zarf surumlu', () => {
  const depo = new BellekDepo()
  const sonuc = gostergeleriKaydet(depo, 'ali', 'AAPL', ['sma20', 'rsi14'], ZAMAN)
  assert.deepEqual(sonuc, { basarili: true })

  const ham = JSON.parse(String(depo.getItem(gostergeAnahtari('ali', 'AAPL'))))
  assert.deepEqual(ham, { v: 1, gostergeler: ['sma20', 'rsi14'], guncelleme_utc: ZAMAN })

  assert.deepEqual(gostergeleriYukle(depo, 'ali', 'AAPL'), { gostergeler: ['sma20', 'rsi14'] })
})

test('GOSTERGE KALICILIK: kayit yoksa bos secim, uyari yok', () => {
  assert.deepEqual(gostergeleriYukle(new BellekDepo(), 'ali', 'MSFT'), { gostergeler: [] })
})

test('GOSTERGE KALICILIK: bos secim de kaydedilir ve bos doner (kaldir -> yenile -> kaldirilmis kalir)', () => {
  const depo = new BellekDepo()
  gostergeleriKaydet(depo, 'ali', 'AAPL', ['macd'], ZAMAN)
  gostergeleriKaydet(depo, 'ali', 'AAPL', [], ZAMAN + 1)
  assert.deepEqual(gostergeleriYukle(depo, 'ali', 'AAPL'), { gostergeler: [] })
})

test('GOSTERGE KALICILIK (Y7): A kullanicisinin secimi ayni tarayicida B-ye GORUNMEZ', () => {
  const depo = new BellekDepo() // tek cihaz, iki hesap
  gostergeleriKaydet(depo, 'kullanici-A', 'AAPL', ['bollinger20'], ZAMAN)
  assert.deepEqual(gostergeleriYukle(depo, 'kullanici-B', 'AAPL'), { gostergeler: [] })
  gostergeleriKaydet(depo, 'kullanici-B', 'AAPL', ['ema20'], ZAMAN)
  assert.deepEqual(gostergeleriYukle(depo, 'kullanici-A', 'AAPL').gostergeler, ['bollinger20'])
  assert.deepEqual(gostergeleriYukle(depo, 'kullanici-B', 'AAPL').gostergeler, ['ema20'])
})

test('GOSTERGE KALICILIK: sembol basina ayri - AAPL secimi TSLA-ya tasinmaz, harf farki ayni kaydi acar', () => {
  const depo = new BellekDepo()
  gostergeleriKaydet(depo, 'ali', 'aapl', ['sma50'], ZAMAN)
  assert.deepEqual(gostergeleriYukle(depo, 'ali', 'AAPL').gostergeler, ['sma50'])
  assert.deepEqual(gostergeleriYukle(depo, 'ali', 'TSLA').gostergeler, [])
})

test('GOSTERGE KALICILIK: yuklenen liste kanonik siraya dizilir, tekrarlar tek kalir', () => {
  const depo = new BellekDepo()
  depo.setItem(
    gostergeAnahtari('ali', 'AAPL'),
    JSON.stringify({ v: 1, gostergeler: ['macd', 'sma20', 'macd'], guncelleme_utc: ZAMAN }),
  )
  assert.deepEqual(gostergeleriYukle(depo, 'ali', 'AAPL'), { gostergeler: ['sma20', 'macd'] })
})

test('GOSTERGE KALICILIK: sil kaydi kaldirir, olmayan anahtarda da firlatmaz', () => {
  const depo = new BellekDepo()
  gostergeleriKaydet(depo, 'ali', 'AAPL', ['sma20'], ZAMAN)
  assert.deepEqual(gostergeleriSil(depo, 'ali', 'AAPL'), { basarili: true })
  assert.equal(depo.getItem(gostergeAnahtari('ali', 'AAPL')), null)
  assert.deepEqual(gostergeleriSil(depo, 'ali', 'AAPL'), { basarili: true })
})

// ---------------------------------------------------------------- S3: goc ve bozuk veri (Y8 / C4)

/** Depoya ham metin yazip yukler. */
function hamYukle(ham: string): ReturnType<typeof gostergeleriYukle> {
  const depo = new BellekDepo()
  depo.setItem(gostergeAnahtari('ali', 'AAPL'), ham)
  return gostergeleriYukle(depo, 'ali', 'AAPL')
}

test('GOSTERGE KALICILIK: bozuk JSON cokertmez - bos secim + gorunur uyari', () => {
  assert.deepEqual(hamYukle('{bu json degil'), { gostergeler: [], uyari: 'bozuk kayit sifirlandi' })
})

test('GOSTERGE KALICILIK: JSON gecerli ama nesne degil (null, sayi, metin) -> bozuk kayit', () => {
  for (const ham of ['null', '42', '"sma20"', 'true']) {
    assert.deepEqual(hamYukle(ham), { gostergeler: [], uyari: 'bozuk kayit sifirlandi' }, ham)
  }
})

test('GOSTERGE KALICILIK: eksik alan - gostergeler yoksa ya da dizi degilse bozuk kayit', () => {
  assert.deepEqual(hamYukle(JSON.stringify({ v: 1 })), { gostergeler: [], uyari: 'bozuk kayit sifirlandi' })
  assert.deepEqual(
    hamYukle(JSON.stringify({ v: 1, gostergeler: 'sma20' })),
    { gostergeler: [], uyari: 'bozuk kayit sifirlandi' },
  )
})

test('GOSTERGE KALICILIK: guncelleme_utc eksikse kayit yine gecerli (bilgi alani, C3)', () => {
  assert.deepEqual(hamYukle(JSON.stringify({ v: 1, gostergeler: ['rsi14'] })), { gostergeler: ['rsi14'] })
})

test('GOSTERGE KALICILIK: bilinmeyen surum sessizce yorumlanmaz - sifirlama + uyari', () => {
  const sonuc = hamYukle(JSON.stringify({ v: 2, gostergeler: ['sma20'] }))
  assert.deepEqual(sonuc, { gostergeler: [], uyari: 'bilinmeyen surum (v=2) sifirlandi' })
  // v alani hic yoksa da ayni yol (undefined != 1).
  assert.match(String(hamYukle(JSON.stringify({ gostergeler: ['sma20'] })).uyari), /bilinmeyen surum \(v=undefined\)/)
})

test('GOSTERGE KALICILIK: zarfsiz eski kayit (v0 duz dizi) goc edilir, goc uyarida gorunur', () => {
  assert.deepEqual(hamYukle(JSON.stringify(['macd', 'sma20'])), {
    gostergeler: ['sma20', 'macd'],
    uyari: 'eski surum (v0) goc edildi',
  })
})

test('GOSTERGE KALICILIK: taninmayan kimlikler atlanir ve KAC tanesi atlandigi yazilir', () => {
  const sonuc = hamYukle(JSON.stringify({ v: 1, gostergeler: ['sma20', 'vwap', 7, null, 'ichimoku'] }))
  assert.deepEqual(sonuc, { gostergeler: ['sma20'], uyari: '4 gosterge taninmadigi icin atlandi' })
})

test('GOSTERGE KALICILIK: depo okunamiyorsa (gizli mod) cokme yok, uyari var', () => {
  const depo = new BellekDepo()
  depo.getItem = () => {
    throw new Error('SecurityError: depolama erisimi engellendi')
  }
  const sonuc = gostergeleriYukle(depo, 'ali', 'AAPL')
  assert.deepEqual(sonuc.gostergeler, [])
  assert.match(String(sonuc.uyari), /^depo okunamadi: /)
})

test('GOSTERGE KALICILIK: yukle YAN ETKISIZDIR - bozuk kayit depoda oldugu gibi kalir, yazim yok', () => {
  const depo = new BellekDepo()
  const anahtar = gostergeAnahtari('ali', 'AAPL')
  depo.setItem(anahtar, 'bozuk')
  const onceki = depo.yazimSayisi
  gostergeleriYukle(depo, 'ali', 'AAPL')
  assert.equal(depo.getItem(anahtar), 'bozuk')
  assert.equal(depo.yazimSayisi, onceki)
})

// ---------------------------------------------------------------- S4: kota (Y9)

/** Gercek tarayicilarin kota hatasi bicimleri (Chromium/WebKit ve eski Firefox). */
function kotaHatasi(ad: string): Error {
  const hata = new Error('depolama kotasi doldu')
  hata.name = ad
  return hata
}

test('GOSTERGE KALICILIK (Y9): kota asimi FIRLATMAZ - basarisiz + kotaDoldu isareti', () => {
  const depo = new BellekDepo()
  depo.setItem = () => {
    throw kotaHatasi('QuotaExceededError')
  }
  const sonuc = gostergeleriKaydet(depo, 'ali', 'AAPL', ['sma20'], ZAMAN)
  assert.equal(sonuc.basarili, false)
  assert.equal(sonuc.kotaDoldu, true)
  assert.match(String(sonuc.hata), /QuotaExceededError/)
})

test('GOSTERGE KALICILIK (Y9): kota disi yazma hatasi kota diye etiketlenmez', () => {
  const depo = new BellekDepo()
  depo.setItem = () => {
    throw kotaHatasi('SecurityError')
  }
  const sonuc = gostergeleriKaydet(depo, 'ali', 'AAPL', ['sma20'], ZAMAN)
  assert.equal(sonuc.basarili, false)
  assert.equal(sonuc.kotaDoldu, undefined)
})
