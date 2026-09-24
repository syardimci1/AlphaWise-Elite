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
