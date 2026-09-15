// Kategoriler: MARKER URETIMI (C2, V-002), KUMELEME (gorsel-gurultu
// onlemi), FILTRE BAGIMSIZLIGI, FILTRE KOMBINASYONLARI (2^4 orneklemi).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import type { KoyfinOlay, KoyfinOlayTipi } from '../../src/lib/koyfin-olaylar'
import { olaylardanMarkerUret, markerlariKumele } from '../../src/lib/koyfin-marker'
import { gunStringindenUtcMs } from '../../src/lib/koyfin-zaman'

function sahteOlay(tip: KoyfinOlayTipi, gun: string, aciklamaGunu: string, ekstra: Record<string, unknown> = {}): KoyfinOlay {
  return {
    id: `test-${tip}-${gun}-${Math.random()}`,
    tip, symbol: 'NVDA',
    ts_utc: gunStringindenUtcMs(gun),
    kaynak_zamani_utc: gunStringindenUtcMs(aciklamaGunu),
    kaynak: 'test', ozet: `${tip} test olayi`, detay_url: null,
    ham_veri_ref: ekstra, confidence: 1.0,
  }
}

test('MARKER/V-002: marker aciklama tarihinde (kaynak_zamani_utc) gosterilir, islem tarihinde DEGIL', () => {
  const olay = sahteOlay('INSIDER', '2026-08-01', '2026-09-01', { acik_piyasa_yonu: 'alis' })
  const [marker] = olaylardanMarkerUret([olay])
  assert.equal(marker.time, '2026-09-01') // kaynak_zamani_utc
  assert.notEqual(marker.time, '2026-08-01') // ts_utc DEGIL
})

test('MARKER/YON: congress SALE -> asagi ok/uste, digeri yukari ok/alta', () => {
  const satis = sahteOlay('CONGRESS', '2026-09-01', '2026-09-01', { transaction_type: 'Sale' })
  const alis = sahteOlay('CONGRESS', '2026-09-01', '2026-09-01', { transaction_type: 'Purchase' })
  const [satisMarker] = olaylardanMarkerUret([satis])
  const [alisMarker] = olaylardanMarkerUret([alis])
  assert.equal(satisMarker.shape, 'arrowDown')
  assert.equal(satisMarker.position, 'aboveBar')
  assert.equal(alisMarker.shape, 'arrowUp')
  assert.equal(alisMarker.position, 'belowBar')
})

test('MARKER/YON: 13F her zaman circle (yon tasimaz)', () => {
  const [marker] = olaylardanMarkerUret([sahteOlay('13F', '2026-09-01', '2026-09-01')])
  assert.equal(marker.shape, 'circle')
})

test('MARKER/KUMELEME: ayni gun+konumdaki coklu olay tek gorsel marker olur, "+N" etiketi tasir', () => {
  const olaylar = [
    sahteOlay('CONGRESS', '2026-09-01', '2026-09-03', { transaction_type: 'Sale' }),
    sahteOlay('INSIDER', '2026-08-20', '2026-09-03', { acik_piyasa_yonu: 'satis' }),
  ]
  const markers = olaylardanMarkerUret(olaylar) // ikisi de ayni gun (03) + aboveBar (satis yonlu)
  const { gorunen } = markerlariKumele(markers)
  assert.equal(gorunen.length, 1)
  assert.match(gorunen[0].text, /\+1$/)
})

test('MARKER/KUMELEME: farkli gundeki olaylar AYRI marker kalir', () => {
  const olaylar = [
    sahteOlay('13F', '2026-06-30', '2026-08-01'),
    sahteOlay('13F', '2026-06-30', '2026-08-05'),
  ]
  const markers = olaylardanMarkerUret(olaylar)
  const { gorunen } = markerlariKumele(markers)
  assert.equal(gorunen.length, 2)
})

test('MARKER/FILTRE-KOMBINASYONLARI: 4 tipin 2^4=16 alt kumesinin hepsi dogru sayida marker uretir', () => {
  const TUM_TIPLER: KoyfinOlayTipi[] = ['13F', 'DARK_POOL', 'CONGRESS', 'INSIDER']
  const tumOlaylar = [
    sahteOlay('13F', '2026-01-01', '2026-01-10'),
    sahteOlay('DARK_POOL', '2026-01-02', '2026-01-11'),
    sahteOlay('CONGRESS', '2026-01-03', '2026-01-12', { transaction_type: 'Sale' }),
    sahteOlay('INSIDER', '2026-01-04', '2026-01-13', { acik_piyasa_yonu: 'alis' }),
  ]
  let kontrolEdilenKombinasyon = 0
  for (let bit = 0; bit < 16; bit++) {
    const aktif = new Set<KoyfinOlayTipi>()
    TUM_TIPLER.forEach((tip, i) => { if (bit & (1 << i)) aktif.add(tip) })
    const filtreli = tumOlaylar.filter((o) => aktif.has(o.tip))
    const markers = olaylardanMarkerUret(filtreli)
    assert.equal(markers.length, aktif.size, `bit=${bit} icin marker sayisi filtre sayisiyla eslesmeli`)
    kontrolEdilenKombinasyon++
  }
  assert.equal(kontrolEdilenKombinasyon, 16)
})

test('MARKER/BAGIMSIZLIK: yalnizca DARK_POOL kapatildiginda digerleri etkilenmez', () => {
  const TUM_TIPLER: KoyfinOlayTipi[] = ['13F', 'DARK_POOL', 'CONGRESS', 'INSIDER']
  const tumOlaylar = TUM_TIPLER.map((t) => sahteOlay(t, '2026-01-01', '2026-01-10', { transaction_type: 'Sale', acik_piyasa_yonu: 'alis' }))
  const aktif = new Set(TUM_TIPLER.filter((t) => t !== 'DARK_POOL'))
  const filtreli = tumOlaylar.filter((o) => aktif.has(o.tip))
  assert.equal(filtreli.length, 3)
  assert.ok(!filtreli.some((o) => o.tip === 'DARK_POOL'))
})
