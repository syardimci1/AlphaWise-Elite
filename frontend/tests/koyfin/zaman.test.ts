// Kategori: ZAMAN (C4) - marker dogru tarihte mi, sinir TZ dahil.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { gunStringindenUtcMs, utcMsToIsGunuString, utcMsToYerelEtiket } from '../../src/lib/koyfin-zaman'

test('ZAMAN: gun stringi UTC gece yarisina cevrilir, yerel TZ karismaz', () => {
  const ms = gunStringindenUtcMs('2026-09-03')
  const d = new Date(ms)
  assert.equal(d.getUTCFullYear(), 2026)
  assert.equal(d.getUTCMonth(), 8) // 0-indeksli: Eylul=8
  assert.equal(d.getUTCDate(), 3)
  assert.equal(d.getUTCHours(), 0)
  assert.equal(d.getUTCMinutes(), 0)
})

test('ZAMAN: yil siniri (31 Aralik -> 1 Ocak) kaymadan calisir', () => {
  const ms = gunStringindenUtcMs('2025-12-31')
  assert.equal(utcMsToIsGunuString(ms), '2025-12-31')
  const ertesi = ms + 24 * 3600 * 1000
  assert.equal(utcMsToIsGunuString(ertesi), '2026-01-01')
})

test('ZAMAN: gunStringindenUtcMs <-> utcMsToIsGunuString round-trip kayipsiz', () => {
  for (const gun of ['2026-01-01', '2026-02-28', '2026-09-15', '2026-12-31']) {
    assert.equal(utcMsToIsGunuString(gunStringindenUtcMs(gun)), gun)
  }
})

test('ZAMAN: yerel etiket bicimlendirmesi cokmez ve tarihi tasir', () => {
  const etiket = utcMsToYerelEtiket(gunStringindenUtcMs('2026-09-03'), 'tr-TR')
  assert.match(etiket, /2026/)
})
