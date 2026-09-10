/**
 * Sinyal kutusu sozlesmesi — madde 46.
 *
 * NEDEN EKLENTI MIMARISI YERINE TEST
 * ==================================
 * OpenTerminalUI'nin eklenti mimarisi fikri sudur: widget'lar kendilerini
 * bir kayda yazar, kabuk yalnizca kayitli olani cizer. Boylece yeni bir
 * widget eklemek kabugu duzenlemeyi gerektirmez ve kabuk her widget'tan
 * belli alanlari ISTEYEBILIR.
 *
 * Bu panelde zaten benzer bir desen var: useSinyal(url) kancasi ve
 * SinyalKutusu bileseni. 11 sinyalin 11'i de bu yoldan geciyor ve
 * olculdu — 11'inin de rozet, uyari ve aciklama alanlari DOLU.
 *
 * Yani eklenti kaydinin saglayacagi TEK ek fayda ZORLAMA idi: bugun
 * 12'nci sinyali uyari alani olmadan eklemek mumkun ve hicbir sey
 * engellemiyor. O zorlamayi bir kayit mimarisi yerine bu test sagliyor -
 * ayni koruma, refactor yok.
 *
 * Eklenti mimarisi SU DURUMDA gerekli olurdu: sinyaller calisma aninda
 * eklenip cikarilabilecekse ya da ucuncu taraflarca yazilacaksa. Ikisi
 * de bu urun icin gecerli degil.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const KOK = join(dirname(fileURLToPath(import.meta.url)), '..')
const PANEL = join(KOK, 'src/app/dashboard/page.tsx')

/** Acilis etiketlerini dengeli sekilde cikarir (ic ice <> kacisi icin). */
function sinyalKutulari(kaynak) {
  const out = []
  let i = 0
  while ((i = kaynak.indexOf('<SinyalKutusu', i)) !== -1) {
    let derinlik = 0
    let j = i + '<SinyalKutusu'.length
    for (; j < kaynak.length; j++) {
      const c = kaynak[j]
      if (c === '{') derinlik++
      else if (c === '}') derinlik--
      else if (c === '>' && derinlik === 0) break
    }
    out.push(kaynak.slice(i, j))
    i = j
  }
  return out
}

const kaynak = readFileSync(PANEL, 'utf8')
const kutular = sinyalKutulari(kaynak)

test('panelde sinyal kutusu bulunuyor (test anlamli olsun)', () => {
  assert.ok(kutular.length >= 10,
    `beklenenden az sinyal kutusu: ${kutular.length}`)
})

test('her sinyal kutusu UYARI alani tasir', () => {
  const eksik = kutular.filter(k => !/\buyari=/.test(k))
  assert.equal(eksik.length, 0,
    'uyari alani olmayan sinyal kutusu var. Bu alan, gostergenin neyi ' +
    'OLCMEDIGINI ve kalibrasyon durumunu soyler; onsuz bir sinyal ' +
    'kullaniciya oldugundan guvenilir gorunur.\n' +
    eksik.map(k => k.slice(0, 120)).join('\n---\n'))
})

test('her sinyal kutusu ROZET alani tasir', () => {
  const eksik = kutular.filter(k => !/\brozet=/.test(k))
  assert.equal(eksik.length, 0,
    'rozet alani olmayan sinyal kutusu var (gostergenin olgunluk/kapsam etiketi)')
})

test('her sinyal kutusu ACIKLAMA alani tasir', () => {
  const eksik = kutular.filter(k => !/\baciklama=/.test(k))
  assert.equal(eksik.length, 0, 'aciklama alani olmayan sinyal kutusu var')
})

test('her sinyal kutusu BASLIK alani tasir', () => {
  const eksik = kutular.filter(k => !/\bbaslik=/.test(k))
  assert.equal(eksik.length, 0, 'baslik alani olmayan sinyal kutusu var')
})

test('uyari metinleri bos birakilmamis', () => {
  const bos = kutular.filter(k => /\buyari=(""|''|\{""\}|\{''\})/.test(k))
  assert.equal(bos.length, 0,
    'uyari alani BOS birakilmis; alanin varligi degil ICERIGI koruyor')
})

test('sinyal cekimi ortak kanca uzerinden yapiliyor', () => {
  // useSinyal disinda dogrudan fetch ile cekilen sinyal olmamali:
  // ortak kanca hata/durum ayrimini tek yerde tutuyor.
  const kancaSayisi = (kaynak.match(/useSinyal\(/g) || []).length
  assert.ok(kancaSayisi >= kutular.length,
    `sinyal kutusu ${kutular.length} ama useSinyal cagrisi ${kancaSayisi} — ` +
    'bazi sinyaller ortak kancayi atlamis olabilir')
})

test('ayristirici ic ice sus parantezleriyle bozulmuyor', () => {
  // Testin kendisi guvenilir mi: kasitli olarak zor bir ornek.
  const ornek = '<SinyalKutusu baslik={`a > b`} uyari={x > 1 ? "e" : "h"}\n  rozet="r" aciklama="a">icerik</SinyalKutusu>'
  const b = sinyalKutulari(ornek)
  assert.equal(b.length, 1)
  assert.ok(/uyari=/.test(b[0]) && /rozet=/.test(b[0]) && /aciklama=/.test(b[0]))
})
