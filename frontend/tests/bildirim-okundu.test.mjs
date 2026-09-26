// Kategori: BILDIRIM MERKEZI OKUNDU/OKUNMADI KALICILIGI (Y10 boslugu)
//
// FAZ 0/1'de dogrulandi: BildirimMerkezi.tsx'te bildirim-bazli okundu
// durumu, localStorage anahtari ya da ayri unread-sayaci HIC yoktu.
// rozetSayisi() her zaman TOPLAM kritik+alarm sayisini donuyordu -
// kullanici panoyu acip baksa bile rozet sifirlanmiyordu. Bu dosya o
// boslugu kapatan saf mantigi test eder (once test, sonra kod - Y6).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  bildirimIdUret,
  okunanAnahtari,
  okunanlariOku,
  okunduIsaretle,
  okunmamisSayi,
  AZAMI_OKUNAN,
} from '../src/lib/bildirim-okundu.js'

function sahteDepo(baslangic = {}) {
  const veri = { ...baslangic }
  return {
    getItem: (k) => (k in veri ? veri[k] : null),
    setItem: (k, v) => { veri[k] = v },
    removeItem: (k) => { delete veri[k] },
    _veri: veri,
  }
}

test('bildirimIdUret: ayni kaynak+zaman+mesaj her zaman ayni id uretir', () => {
  const b = { kaynak: 'r15_gecis', zaman: '2026-09-25T20:47:14', mesaj: 'defter duzlesti' }
  assert.equal(bildirimIdUret(b), bildirimIdUret({ ...b }))
})

test('bildirimIdUret: farkli mesaj farkli id uretir', () => {
  const a = { kaynak: 'r15_gecis', zaman: '2026-09-25T20:47:14', mesaj: 'A' }
  const c = { kaynak: 'r15_gecis', zaman: '2026-09-25T20:47:14', mesaj: 'B' }
  assert.notEqual(bildirimIdUret(a), bildirimIdUret(c))
})

test('okunanAnahtari: kullanici bazli ad alani (gosterge-kalicilik deseniyle tutarli)', () => {
  assert.equal(okunanAnahtari('uid-1'), 'alphawise:bildirim:okundu:v1:uid-1')
  assert.equal(okunanAnahtari('uid-2'), 'alphawise:bildirim:okundu:v1:uid-2')
})

test('okunanlariOku: bos depoda bos Set doner', () => {
  const depo = sahteDepo()
  const s = okunanlariOku(depo, 'uid-1')
  assert.equal(s.size, 0)
})

test('okunduIsaretle + okunanlariOku: yazilan id geri okunur', () => {
  const depo = sahteDepo()
  okunduIsaretle(depo, 'uid-1', 'id-A')
  const s = okunanlariOku(depo, 'uid-1')
  assert.ok(s.has('id-A'))
})

test('okunanlariOku: kullanici ad alani izole - uid-1 yazisi uid-2de gorunmez', () => {
  const depo = sahteDepo()
  okunduIsaretle(depo, 'uid-1', 'id-A')
  const s2 = okunanlariOku(depo, 'uid-2')
  assert.equal(s2.size, 0)
})

test('okunduIsaretle: bozuk JSON varsa sessizce bos sepetten baslar (fail-safe, atmaz)', () => {
  const depo = sahteDepo({ 'alphawise:bildirim:okundu:v1:uid-1': '{bozuk' })
  assert.doesNotThrow(() => okunduIsaretle(depo, 'uid-1', 'id-A'))
  const s = okunanlariOku(depo, 'uid-1')
  assert.ok(s.has('id-A'))
})

test(`okunduIsaretle: ${AZAMI_OKUNAN} siniri asilinca EN ESKI id dusurulur (sinirsiz buyume yok)`, () => {
  const depo = sahteDepo()
  for (let i = 0; i < AZAMI_OKUNAN + 5; i++) okunduIsaretle(depo, 'uid-1', `id-${i}`)
  const s = okunanlariOku(depo, 'uid-1')
  assert.equal(s.size, AZAMI_OKUNAN)
  assert.ok(!s.has('id-0'), 'en eski id sinirin disina dusmeli')
  assert.ok(s.has(`id-${AZAMI_OKUNAN + 4}`), 'en yeni id kalmali')
})

test('okunmamisSayi: kritik+alarm okunmamislar sayilir, uyari/bilgi sayilmaz', () => {
  const bildirimler = [
    { kaynak: 'a', zaman: 't1', mesaj: 'm1', duzey: 'kritik' },
    { kaynak: 'a', zaman: 't2', mesaj: 'm2', duzey: 'alarm' },
    { kaynak: 'a', zaman: 't3', mesaj: 'm3', duzey: 'uyari' },
    { kaynak: 'a', zaman: 't4', mesaj: 'm4', duzey: 'bilgi' },
  ]
  const okunanlar = new Set()
  assert.equal(okunmamisSayi(bildirimler, okunanlar), 2)
})

test('okunmamisSayi: okunmus olarak isaretlenen dusurulur', () => {
  const b1 = { kaynak: 'a', zaman: 't1', mesaj: 'm1', duzey: 'kritik' }
  const b2 = { kaynak: 'a', zaman: 't2', mesaj: 'm2', duzey: 'alarm' }
  const okunanlar = new Set([bildirimIdUret(b1)])
  assert.equal(okunmamisSayi([b1, b2], okunanlar), 1)
})

test('okunmamisSayi: hepsi okunmussa 0 doner (ROZETIN ESAS AMACI - eski davranista rozet asla sifirlanmiyordu)', () => {
  const b1 = { kaynak: 'a', zaman: 't1', mesaj: 'm1', duzey: 'kritik' }
  const okunanlar = new Set([bildirimIdUret(b1)])
  assert.equal(okunmamisSayi([b1], okunanlar), 0)
})

test('okunanlariOku: depo erisimi (private mode gibi) hata atarsa bos Set doner, cokme yok', () => {
  const patlayanDepo = {
    getItem: () => { throw new Error('erisim engellendi') },
    setItem: () => { throw new Error('erisim engellendi') },
  }
  assert.doesNotThrow(() => okunanlariOku(patlayanDepo, 'uid-1'))
  assert.equal(okunanlariOku(patlayanDepo, 'uid-1').size, 0)
})

test('okunduIsaretle: depo erisimi hata atarsa sessizce yutulur, cokme yok', () => {
  const patlayanDepo = {
    getItem: () => null,
    setItem: () => { throw new Error('kota asildi') },
  }
  assert.doesNotThrow(() => okunduIsaretle(patlayanDepo, 'uid-1', 'id-A'))
})

// FAZ 4 — KASTEN KIRMA senaryolari (yeni koda ozgu olanlar; 0 bildirim/tum
// bayat/servis cokuk/rol kapisi zaten bildirim-ozet.test.mjs ve
// bildirimler-rol.test.ts'te kapsanmis).

test('KASTEN KIRMA (4/7 - performans): 500+ bildirimde okunmamisSayi makul surede biter', () => {
  const cok = Array.from({ length: 500 }, (_, i) => ({
    kaynak: `kaynak-${i % 7}`, zaman: `2026-09-${(i % 28) + 1}T00:00:00`,
    mesaj: `mesaj-${i}`, duzey: i % 4 === 0 ? 'kritik' : i % 4 === 1 ? 'alarm' : 'bilgi',
  }))
  const baslangic = process.hrtime.bigint()
  const sonuc = okunmamisSayi(cok, new Set())
  const gecenMs = Number(process.hrtime.bigint() - baslangic) / 1e6
  assert.ok(gecenMs < 200, `500 kayit ${gecenMs}ms surdu, 200ms siniri asildi`)
  assert.equal(sonuc, cok.filter((b) => b.duzey === 'kritik' || b.duzey === 'alarm').length)
})

test('KASTEN KIRMA (5/7 - iki sekme): B sekmesinin yazdigi ayni anahtari A sekmesi okuyabilir (StorageEvent A icin ayni depoyu okur)', () => {
  const ortakDepo = sahteDepo() // gercekte iki sekme AYNI localStorage'i paylasir
  okunduIsaretle(ortakDepo, 'uid-1', 'id-B-sekmesinde-okundu')
  // A sekmesi kendi state'ini tazeledi (BildirimMerkezi.tsx'teki 'storage'
  // dinleyicisi bu okumayi tetikler) - burada dogrudan ayni fonksiyon cagrilir.
  const aSekmesininGordugu = okunanlariOku(ortakDepo, 'uid-1')
  assert.ok(aSekmesininGordugu.has('id-B-sekmesinde-okundu'))
})

test('KASTEN KIRMA (7/7 - gecersiz kullanici kimligi): bos string ve null cokmeden bos/izole davranir', () => {
  const depo = sahteDepo()
  assert.doesNotThrow(() => okunanlariOku(depo, ''))
  assert.doesNotThrow(() => okunanlariOku(depo, null))
  assert.doesNotThrow(() => okunduIsaretle(depo, '', 'id-A'))
  // Bos string kimlikle yazilan, gercek bir kullanici kimligiyle KARISMAZ.
  okunduIsaretle(depo, '', 'id-A')
  assert.equal(okunanlariOku(depo, 'uid-gercek').size, 0)
})
