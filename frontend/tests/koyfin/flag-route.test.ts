// Kategori: FEATURE FLAG (C5) - kapali/acik/onizleme-token davranisi.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { NextRequest } from 'next/server'
import { GET } from '../../src/app/api/config/koyfin-flag/route'

test('FLAG: ana bayrak "0" ve token yoksa enabled=false doner', async () => {
  process.env.KOYFIN_EVENT_OVERLAY_ENABLED = '0'
  delete process.env.KOYFIN_PREVIEW_TOKEN
  const req = new NextRequest('http://localhost/api/config/koyfin-flag')
  const res = await GET(req)
  const gövde = await res.json()
  assert.equal(gövde.enabled, false)
})

test('FLAG: ana bayrak "1" ise enabled=true doner', async () => {
  process.env.KOYFIN_EVENT_OVERLAY_ENABLED = '1'
  const req = new NextRequest('http://localhost/api/config/koyfin-flag')
  const res = await GET(req)
  const gövde = await res.json()
  assert.equal(gövde.enabled, true)
  process.env.KOYFIN_EVENT_OVERLAY_ENABLED = '0'
})

test('FLAG: ana bayrak kapaliyken dogru onizleme token\'i enabled=true yapar', async () => {
  process.env.KOYFIN_EVENT_OVERLAY_ENABLED = '0'
  process.env.KOYFIN_PREVIEW_TOKEN = 'gizli-test-tokeni'
  const dogru = new NextRequest('http://localhost/api/config/koyfin-flag?koyfin_preview=gizli-test-tokeni')
  const yanlis = new NextRequest('http://localhost/api/config/koyfin-flag?koyfin_preview=baska-bir-sey')
  assert.equal((await (await GET(dogru)).json()).enabled, true)
  assert.equal((await (await GET(yanlis)).json()).enabled, false)
  delete process.env.KOYFIN_PREVIEW_TOKEN
})
