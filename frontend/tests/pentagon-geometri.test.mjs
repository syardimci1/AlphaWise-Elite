/**
 * Bes eksen gorselinin geometri testleri.
 *
 * Bagimlilik YOK: node'un yerlesik test kosucusuyla calisir.
 *   node --test frontend/tests/
 * Frontend'de hicbir test cercevesi kurulu olmadigi icin bilincli olarak
 * sifir-bagimlilik secildi; boylece "test altyapisi yok" bahanesi bu
 * gorsel icin gecerli degil.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import {
  kutupsal, eksenNoktalari, poligonKenarlari, halkaYaricaplari,
  halkaNoktalari, etiketKonumu, durumMetni, genelPuanMetni, kapsamMetni,
  ASGARI_POLIGON_KOSESI, OLCULDU, OLCULEMEDI, UYGULANAMAZ,
} from '../src/lib/pentagon-geometri.js'

const M = { x: 100, y: 100 }
const R = 80

const eksen = (anahtar, puan, durum = OLCULDU) => ({
  anahtar, ad: anahtar, puan, durum,
})

function besEksen(puanlar) {
  const adlar = ['saglik', 'kalite', 'guc', 'deger', 'temettu']
  return adlar.map((a, i) => {
    const p = puanlar[i]
    if (p === null) return eksen(a, null, OLCULEMEDI)
    if (p === 'uyg') return eksen(a, null, UYGULANAMAZ)
    return eksen(a, p, OLCULDU)
  })
}

// ------------------------------------------------------------- kutupsal
test('ilk eksen tam tepede baslar', () => {
  const p = kutupsal(M, R, 0, 5)
  assert.ok(Math.abs(p.x - M.x) < 1e-9, `x merkezde olmali: ${p.x}`)
  assert.ok(Math.abs(p.y - (M.y - R)) < 1e-9, `y yukarida olmali: ${p.y}`)
})

test('bes eksen esit aciyla dagilir', () => {
  const noktalar = [0, 1, 2, 3, 4].map((i) => kutupsal(M, R, i, 5))
  const uzakliklar = noktalar.map((p) => Math.hypot(p.x - M.x, p.y - M.y))
  for (const u of uzakliklar) assert.ok(Math.abs(u - R) < 1e-9)
  // Ardisik noktalar arasi mesafe esit olmali (duzgun besgen)
  const kenar = (a, b) => Math.hypot(a.x - b.x, a.y - b.y)
  const k0 = kenar(noktalar[0], noktalar[1])
  for (let i = 0; i < 5; i++) {
    assert.ok(Math.abs(kenar(noktalar[i], noktalar[(i + 1) % 5]) - k0) < 1e-9)
  }
})

// ------------------------------------------------- EN KRITIK SOZLESME
test('olculemeyen eksenin KOSESI YOKTUR (null), sifir DEGILDIR', () => {
  const n = eksenNoktalari(besEksen([80, null, 60, 70, 90]), M, R)
  assert.equal(n[1].tepe, null, 'olculemeyen eksene kose cizilmemeli')
  assert.equal(n[1].puan, null)
})

test('uygulanamaz eksenin de KOSESI YOKTUR', () => {
  const n = eksenNoktalari(besEksen([80, 70, 60, 70, 'uyg']), M, R)
  assert.equal(n[4].tepe, null)
  assert.equal(n[4].durum, UYGULANAMAZ)
})

test('OLCULMUS SIFIR merkezde bir kose URETIR (olculemediyle ayni degil)', () => {
  const n = eksenNoktalari(besEksen([0, null, 60, 70, 90]), M, R)
  assert.notEqual(n[0].tepe, null, 'olculmus sifir bir kosedir')
  assert.ok(Math.abs(n[0].tepe.x - M.x) < 1e-9)
  assert.ok(Math.abs(n[0].tepe.y - M.y) < 1e-9)
  // Ayni gorselde olculemeyenin kosesi YOK, olculmus sifirin VAR:
  assert.equal(n[1].tepe, null)
})

test('yuz puan dis cembere oturur', () => {
  const n = eksenNoktalari(besEksen([100, 100, 100, 100, 100]), M, R)
  for (const p of n) {
    assert.ok(Math.abs(Math.hypot(p.tepe.x - M.x, p.tepe.y - M.y) - R) < 1e-9)
  }
})

test('aralik disi puanlar kirpilir', () => {
  const n = eksenNoktalari(besEksen([150, -20, 60, 70, 90]), M, R)
  const uzaklik = (p) => Math.hypot(p.tepe.x - M.x, p.tepe.y - M.y)
  assert.ok(Math.abs(uzaklik(n[0]) - R) < 1e-9, '100 ustu dis cembere kirpilmali')
  assert.ok(Math.abs(uzaklik(n[1])) < 1e-9, 'negatif merkeze kirpilmali')
})

// ------------------------------------------------------------- poligon
test('ucten az olculmus eksende poligon CIZILMEZ', () => {
  const n = eksenNoktalari(besEksen([80, null, null, null, 60]), M, R)
  assert.deepEqual(poligonKenarlari(n), [], 'iki kose bir alan tanimlamaz')
  assert.equal(ASGARI_POLIGON_KOSESI, 3)
})

test('bes eksen de olculduyse bes kenar, atlama YOK', () => {
  const n = eksenNoktalari(besEksen([80, 70, 60, 50, 40]), M, R)
  const k = poligonKenarlari(n)
  assert.equal(k.length, 5)
  assert.ok(k.every((x) => x.atlamaVar === false))
})

test('atlanan eksenin uzerinden gecen kenar ISARETLENIR', () => {
  // 1. eksen (indeks 1) olculemedi -> 0->2 kenari onun uzerinden atlar
  const n = eksenNoktalari(besEksen([80, null, 60, 50, 40]), M, R)
  const k = poligonKenarlari(n)
  assert.equal(k.length, 4)
  const atlayan = k.filter((x) => x.atlamaVar)
  assert.equal(atlayan.length, 1, 'tam bir kenar atlama isaretli olmali')
  assert.equal(atlayan[0].aIndeks, 0)
  assert.equal(atlayan[0].bIndeks, 2)
})

test('tam ucte kose varken poligon kapanir', () => {
  const n = eksenNoktalari(besEksen([80, null, 60, null, 40]), M, R)
  const k = poligonKenarlari(n)
  assert.equal(k.length, 3, 'uc kose -> uc kenar (kapali)')
  assert.equal(k[k.length - 1].bIndeks, 0, 'son kenar basa donmeli')
})

// -------------------------------------------------------------- metinler
test('durum metni olculemeyene SAYI YAZMAZ', () => {
  assert.equal(durumMetni({ puan: null, durum: OLCULEMEDI }), 'veri yok')
  assert.equal(durumMetni({ puan: null, durum: UYGULANAMAZ }), 'uygulanamaz')
  assert.equal(durumMetni({ puan: 0, durum: OLCULDU }), '0')
  assert.equal(durumMetni({ puan: 74.3, durum: OLCULDU }), '74')
})

test('genel puan yoksa tire yazar, sifir YAZMAZ', () => {
  assert.equal(genelPuanMetni(null), '—')
  assert.equal(genelPuanMetni(undefined), '—')
  assert.equal(genelPuanMetni(0), '0')
  assert.equal(genelPuanMetni(74.3), '74')
})

test('kapsam metni olculen eksen sayisini dogru sayar', () => {
  const k = kapsamMetni(besEksen([80, null, 60, 'uyg', 40]), 3)
  assert.equal(k.olculen, 3)
  assert.equal(k.toplam, 5)
  assert.equal(k.yeterli, true)
  assert.equal(k.metin, '3/5 eksen ölçüldü')
})

test('kapsam esigin altindaysa yeterli DEGIL', () => {
  const k = kapsamMetni(besEksen([80, null, null, 'uyg', 40]), 3)
  assert.equal(k.olculen, 2)
  assert.equal(k.yeterli, false)
})

// --------------------------------------------------------------- izgara
test('halka yaricaplari kademelerle orantili', () => {
  const h = halkaYaricaplari(80)
  assert.deepEqual(h.map((x) => x.kademe), [25, 50, 75, 100])
  assert.equal(h[3].yaricap, 80)
  assert.equal(h[1].yaricap, 40)
})

test('halka noktalari kenar sayisi kadar kose uretir', () => {
  const p = halkaNoktalari(M, R, 5).split(' ')
  assert.equal(p.length, 5)
})

test('etiket hizasi yana gore degisir', () => {
  const ust = etiketKonumu(M, R, 0, 5)
  assert.equal(ust.hiza, 'middle', 'tepedeki etiket ortalanir')
  const sag = etiketKonumu(M, R, 1, 5)
  assert.equal(sag.hiza, 'start', 'sagdaki etiket disa yaslanir')
  const sol = etiketKonumu(M, R, 4, 5)
  assert.equal(sol.hiza, 'end', 'soldaki etiket ice yaslanir')
})

test('kisa ad uzun etiketleri grafikte kirpar, kisalari birakir', async () => {
  const { kisaAd } = await import('../src/lib/pentagon-geometri.js')
  assert.equal(kisaAd('Temel Güç'), 'Temel Güç')
  assert.equal(kisaAd('Değerleme'), 'Değerleme')
  assert.equal(kisaAd('Temettü Dayanıklılığı'), 'Temettü')
  assert.equal(kisaAd('Finansal Sağlık'), 'Finansal')
  assert.equal(kisaAd(''), '')
  assert.equal(kisaAd(null), '')
})
