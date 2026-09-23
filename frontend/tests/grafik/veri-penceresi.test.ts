// Kategori: VERI PENCERESI (R4) — /price proxy'sine gecirilen `limit` dogrulamasi.
//
// KONUM NEDEN BURASI: package.json test komutu `tests/*/*.test.ts` glob'u
// kullaniyor; `tests/veri-penceresi.test.ts` (kokte) HIC CALISMAZ ve hata da
// vermez. Bu dosya `tests/grafik/` altinda oldugu icin gercekten kosar.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { NextRequest } from 'next/server'
import {
  limitDogrula,
  limitSorguDizesi,
  LIMIT_ALT,
  LIMIT_UST,
} from '../../src/lib/grafik/veri-penceresi'

test('LIMIT: parametre yoksa "yok" doner — eski cagiranlarin davranisi degismez', () => {
  assert.equal(limitDogrula(null).durum, 'yok')
  assert.equal(limitDogrula(undefined).durum, 'yok')
  assert.equal(limitDogrula('').durum, 'yok')
  assert.equal(limitSorguDizesi({ durum: 'yok' }), '')
})

test('LIMIT: gecerli tam sayilar kabul edilir ve sorgu dizesine cevrilir', () => {
  const s = limitDogrula('1500')
  assert.deepEqual(s, { durum: 'gecerli', limit: 1500 })
  assert.equal(limitSorguDizesi(s), '?limit=1500')
})

test('LIMIT: sinir degerleri — alt ve ust sinirin KENDISI gecerlidir', () => {
  assert.deepEqual(limitDogrula(String(LIMIT_ALT)), { durum: 'gecerli', limit: LIMIT_ALT })
  assert.deepEqual(limitDogrula(String(LIMIT_UST)), { durum: 'gecerli', limit: LIMIT_UST })
})

test('LIMIT: sinirin bir disi reddedilir (kapali aralik kilitlendi)', () => {
  assert.equal(limitDogrula(String(LIMIT_ALT - 1)).durum, 'gecersiz')
  assert.equal(limitDogrula(String(LIMIT_UST + 1)).durum, 'gecersiz')
})

test('LIMIT: sayi olmayan bicimler SESSIZCE yok sayilmaz, gecersiz sayilir', () => {
  // Number() bunlarin hepsini sayiya cevirebilir; bicim kontrolu olmasa
  // '0x10' -> 16, ' 12 ' -> 12, '1e3' -> 1000 olarak GECERDI.
  for (const ham of ['abc', '0x10', '1e3', '12.5', ' 12 ', '-5', '+7', '١٢']) {
    const s = limitDogrula(ham)
    assert.equal(s.durum, 'gecersiz', `"${ham}" gecersiz sayilmaliydi, gelen: ${s.durum}`)
  }
})

test('LIMIT: guvenli tam sayi siniri asan deger "cok buyuk" ile reddedilir', () => {
  const s = limitDogrula('9'.repeat(30))
  assert.equal(s.durum, 'gecersiz')
  assert.equal(s.durum === 'gecersiz' && s.sebep, 'limit cok buyuk')
})

test('LIMIT: gecersiz sonuc sorgu dizesi URETMEZ (yukari akisa sizmaz)', () => {
  assert.equal(limitSorguDizesi({ durum: 'gecersiz', sebep: 'x' }), '')
})

// --- Rota entegrasyonu: dogrulama gercekten BAGLI mi? ----------------------
// Saf fonksiyon yesil olup rotada cagrilmasaydi testler yine gecerdi.
// Asagidaki iki test o bosluğu kapatir.

test('ROTA: gecersiz limit 400 ve anlamli hata doner (fail-loud)', async () => {
  const { GET } = await import('../../src/app/api/market-data/[ticker]/route')
  const req = new NextRequest('http://localhost/api/market-data/MSFT?limit=abc')
  const res = await GET(req, { params: Promise.resolve({ ticker: 'MSFT' }) })
  assert.equal(res.status, 400)
  const govde = await res.json()
  assert.match(govde.hata, /limit/i)
})

test('ROTA: gecersiz ticker kontrolu limit kontrolunden ONCE calisir', async () => {
  // Ikisi de bozuksa donen hata TICKER hatasi olmalidir: dar girdi
  // dogrulamasi her zaman once gelir, boylece bozuk sembol hicbir kod
  // yolunda ilerlemez.
  const { GET } = await import('../../src/app/api/market-data/[ticker]/route')
  const req = new NextRequest('http://localhost/api/market-data/A..?limit=abc')
  const res = await GET(req, { params: Promise.resolve({ ticker: 'A..' }) })
  assert.equal(res.status, 400)
  const govde = await res.json()
  assert.match(govde.hata, /hisse kodu/i)
})
