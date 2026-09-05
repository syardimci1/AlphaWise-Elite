import test from 'node:test'
import assert from 'node:assert/strict'
import { durumOzeti, rozetSayisi, duzeyRengi, kaynakEtiketi }
  from '../src/lib/bildirim-ozet.js'

const ozet = (toplam, okunamayan, kritik = 0, alarm = 0) => ({
  toplam_olay: toplam, okunamayan_kaynak: okunamayan,
  duzey_sayimi: { kritik, alarm, uyari: 0, bilgi: 0 },
})

test('hicbir olay yok ve tum kaynaklar okunduysa "alarm yok" denir', () => {
  const d = durumOzeti(ozet(0, 0))
  assert.equal(d.metin, 'Açık alarm yok')
  assert.equal(d.vurgulu, false)
})

test('EN KRITIK: liste bos ama kaynak okunamadiysa "alarm yok" YAZILMAZ', () => {
  const d = durumOzeti(ozet(0, 2))
  assert.ok(!d.metin.includes('Açık alarm yok'), 'yanlis sessizlik mesaji')
  assert.match(d.metin, /okunamadı/)
  assert.match(d.metin, /DEĞİLDİR/)
  assert.equal(d.vurgulu, true, 'bu durum vurgulanmali')
})

test('servis hic yanit vermediyse sessiz kalinmaz', () => {
  const d = durumOzeti(null)
  assert.match(d.metin, /yanıt vermedi/)
  assert.equal(d.vurgulu, true)
})

test('olay varken sayilar ozetlenir', () => {
  const d = durumOzeti(ozet(8, 0, 0, 8))
  assert.match(d.metin, /8 açık kayıt/)
  assert.equal(d.vurgulu, false, 'kritik yoksa vurgu gerekmez')
})

test('kritik varsa vurgulanir ve sayisi yazilir', () => {
  const d = durumOzeti(ozet(9, 0, 1, 8))
  assert.match(d.metin, /1 kritik/)
  assert.equal(d.vurgulu, true)
  assert.equal(d.renk, '#f87171')
})

test('olay VE okunamayan kaynak birlikte bildirilir', () => {
  const d = durumOzeti(ozet(3, 1, 0, 3))
  assert.match(d.metin, /3 açık kayıt/)
  assert.match(d.metin, /1 kaynak okunamadı/)
  assert.equal(d.vurgulu, true)
})

test('rozet yalnizca kritik ve alarmi sayar', () => {
  assert.equal(rozetSayisi({ duzey_sayimi: { kritik: 2, alarm: 3, uyari: 9, bilgi: 40 } }), 5)
  assert.equal(rozetSayisi(null), 0)
})

test('kaynak etiketi okunamadiyi VURGULU gosterir', () => {
  assert.equal(kaynakEtiketi('okundu').metin, 'okundu')
  assert.equal(kaynakEtiketi('kaynak_yok').metin, 'kaynak yok')
  assert.equal(kaynakEtiketi('okunamadi').metin, 'OKUNAMADI')
  assert.notEqual(kaynakEtiketi('okunamadi').renk, kaynakEtiketi('okundu').renk)
})

test('duzey rengi bilinmeyen duzeyde cokmez', () => {
  assert.ok(duzeyRengi('kritik'))
  assert.equal(duzeyRengi('bilinmeyen'), duzeyRengi('bilgi'))
})
