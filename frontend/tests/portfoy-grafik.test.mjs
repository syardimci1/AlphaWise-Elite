import test from 'node:test'
import assert from 'node:assert/strict'
import { parcalar, yol, olcek, kademeler, paraKisa, KENAR }
  from '../src/lib/portfoy-grafik.js'

const ALAN = { genislik: 300, yukseklik: 150 }
const N = (gun, maliyet, deger) => ({ gun, maliyet, deger })

test('EN KRITIK: olculemeyen nokta cizgiyi KIRAR, atlanarak gecilmez', () => {
  const p = parcalar([N('1', 100, 100), N('2', 100, null), N('3', 100, 120)], ALAN)
  assert.equal(p.deger.length, 2, 'iki ayri parca olmali (bosluk korunmali)')
  assert.equal(p.deger[0].length, 1)
  assert.equal(p.deger[1].length, 1)
  assert.equal(p.maliyet.length, 1, 'maliyet kesintisiz oldugu icin tek parca')
})

test('olculemeyen nokta SIFIR olarak da cizilmez', () => {
  const p = parcalar([N('1', 100, 100), N('2', 100, null)], ALAN)
  const tumY = p.deger.flat().map((q) => q.y)
  assert.equal(tumY.length, 1, 'yalnizca olculen nokta cizilmeli')
})

test('bastaki ve sondaki bosluklar parca uretmez', () => {
  const p = parcalar([N('1', 100, null), N('2', 100, 110), N('3', 100, null)], ALAN)
  assert.equal(p.deger.length, 1)
  assert.equal(p.deger[0].length, 1)
})

test('iki seri AYNI olcekte cizilir (cift eksen yok)', () => {
  /* Maliyet 100, deger 200 ise ikisi ayni y-olceginden gecmeli; ayri
     olcekler iki seriyi keyfi noktada kesistirirdi. */
  const p = parcalar([N('1', 100, 200), N('2', 100, 200)], ALAN)
  const yMaliyet = p.maliyet[0][0].y
  const yDeger = p.deger[0][0].y
  assert.ok(yMaliyet > yDeger, 'kucuk deger asagida olmali (y ters cevrilmis)')
  // Ayni olcek: maliyet en dusuk -> en altta, deger en yuksek -> en ustte
  assert.ok(Math.abs(yDeger - KENAR.ust) < 0.01)
})

test('tek noktali seri ortada cizilir, cokmez', () => {
  const p = parcalar([N('1', 100, 110)], ALAN)
  assert.equal(p.deger[0].length, 1)
  assert.ok(p.deger[0][0].x > KENAR.sol)
})

test('bos seri cokmez', () => {
  const p = parcalar([], ALAN)
  assert.deepEqual(p.deger, [])
  assert.equal(p.y, null)
})

test('duz seride sifira bolme olmaz', () => {
  const f = olcek([100, 100, 100], 120, true)
  assert.ok(Number.isFinite(f(100)))
})

test('yol dizgisi SVG bicimine uygun', () => {
  const p = parcalar([N('1', 100, 100), N('2', 100, 120)], ALAN)
  const d = yol(p.deger[0])
  assert.match(d, /^\d+\.\d,\d+\.\d \d+\.\d,\d+\.\d$/)
})

test('kademeler alt ve ust siniri icerir', () => {
  const k = kademeler([10, 50, 90], 3)
  assert.equal(k[0], 10)
  assert.equal(k[k.length - 1], 90)
})

test('kademeler duz seride tek deger doner', () => {
  assert.deepEqual(kademeler([42, 42]), [42])
})

test('para bicimi olculemedigi TIRE ile gosterir', () => {
  assert.equal(paraKisa(null), '—')
  assert.equal(paraKisa(NaN), '—')
  assert.equal(paraKisa(0), '0', 'olculmus sifir tire olamaz')
})

test('eksen etiketi BELIRSIZ kisaltma kullanmaz', () => {
  /* Ilk surum 9987.72 icin "10.0B" yaziyordu: Turkce "bin", Ingilizce
     "billion" olarak okunabilirdi. Binler mertebesinde kisaltma gereksiz. */
  assert.equal(paraKisa(9987.72), '9.988')
  assert.equal(paraKisa(1476.45), '1.476')
  assert.ok(!paraKisa(9987.72).includes('B'), 'belirsiz B eki kullanilmamali')
})

test('milyon ustunde BELIRSIZ OLMAYAN ek kullanilir', () => {
  assert.equal(paraKisa(2_500_000), '2,5 mn')
  assert.ok(!paraKisa(2_500_000).includes('M'), 'tek harfli belirsiz ek olmamali')
})
