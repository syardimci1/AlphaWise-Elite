/**
 * Arama akisi testleri — madde 45.
 *
 * Kilitlenen tek sey: uc istek de AYNI ANDA baslamali. Biri otekini
 * bekliyorsa kullanici iki bekleme suresini ust uste yasar.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { aramaAkisiBaslat, sembolNormalize } from '../src/lib/arama-akisi.js'

/** Cagri sirasini kaydeden, elle cozulen sahte getirici. */
function sahteGetirici() {
  const cagrilar = []
  const cozucular = []
  const getir = (url) => {
    cagrilar.push(url)
    return new Promise((coz) => cozucular.push({ url, coz }))
  }
  return { getir, cagrilar, cozucular }
}

test('uc istek de HICBIRI cozulmeden once baslar', () => {
  const { getir, cagrilar } = sahteGetirici()
  aramaAkisiBaslat('msft', getir)
  // Hicbir promise cozulmedi; buna ragmen ucu de cagrilmis olmali.
  assert.equal(cagrilar.length, 3,
    `es zamanli baslamadi, cagrilan: ${JSON.stringify(cagrilar)}`)
})

test('MAA yaniti beklenmeden godmode istegi baslar', () => {
  const { getir, cagrilar } = sahteGetirici()
  aramaAkisiBaslat('MSFT', getir)
  const godmode = cagrilar.find(u => u.includes('/api/godmode/'))
  assert.ok(godmode, 'godmode istegi hic baslamadi')
  assert.ok(godmode.includes('MSFT'))
})

test('ucu de dogru uc noktalara gider', () => {
  const { getir, cagrilar } = sahteGetirici()
  aramaAkisiBaslat('NVDA', getir)
  assert.ok(cagrilar.some(u => u === '/api/maa/narrative-verified/NVDA'))
  assert.ok(cagrilar.some(u => u === '/api/maa/memory/NVDA'))
  assert.ok(cagrilar.some(u => u === '/api/godmode/NVDA'))
})

test('sembol buyuk harfe cevrilir ve bosluk kirpilir', () => {
  const { getir, cagrilar } = sahteGetirici()
  aramaAkisiBaslat('  wdc  ', getir)
  assert.ok(cagrilar.every(u => u.endsWith('WDC')),
    `normalize edilmedi: ${JSON.stringify(cagrilar)}`)
})

test('donen nesne uc promise tasir', () => {
  const { getir } = sahteGetirici()
  const a = aramaAkisiBaslat('MSFT', getir)
  for (const ad of ['maa', 'hafiza', 'godmode']) {
    assert.ok(a[ad] instanceof Promise, `${ad} promise degil`)
  }
})

test('biri gec cozulse bile digerleri bagimsiz cozulur', async () => {
  const { getir, cozucular } = sahteGetirici()
  const a = aramaAkisiBaslat('MSFT', getir)
  // MAA hic cozulmeden godmode cozulebilmeli
  cozucular.find(c => c.url.includes('/godmode/')).coz({ ok: true })
  const g = await a.godmode
  assert.deepEqual(g, { ok: true })
})

test('bos ticker reddedilir', () => {
  const { getir } = sahteGetirici()
  for (const bos of ['', '   ', null, undefined]) {
    assert.throws(() => aramaAkisiBaslat(bos, getir), /ticker bos olamaz/)
  }
})

test('getir fonksiyon degilse reddedilir', () => {
  assert.throws(() => aramaAkisiBaslat('MSFT', null), /fonksiyon olmali/)
  assert.throws(() => aramaAkisiBaslat('MSFT', 'yok'), /fonksiyon olmali/)
})

test('ozel karakterli sembol URL icin kacisli yazilir', () => {
  const { getir, cagrilar } = sahteGetirici()
  aramaAkisiBaslat('BRK.B', getir)
  assert.ok(cagrilar.every(u => u.includes('BRK.B') || u.includes('BRK%2EB')),
    `beklenmeyen kodlama: ${JSON.stringify(cagrilar)}`)
  aramaAkisiBaslat('A/B', getir)
  assert.ok(cagrilar.some(u => u.includes('A%2FB')),
    'yol ayraci kacisli yazilmadi')
})

test('sembolNormalize page.tsx ile ayni kurali uygular', () => {
  assert.equal(sembolNormalize('  msft '), 'MSFT')
  assert.equal(sembolNormalize(''), '')
  assert.equal(sembolNormalize(null), '')
})
