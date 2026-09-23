// Kategori: FEATURE FLAG (Y7) — grafik terminali varsayilan KAPALI olmali.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { NextRequest } from 'next/server'
import { GET } from '../../src/app/api/config/grafik-flag/route'

const istek = (sorgu = '') =>
  new NextRequest(`http://localhost/api/config/grafik-flag${sorgu}`)

test('FLAG: degisken HIC TANIMLI DEGILSE enabled=false (Y7 varsayilan kapali)', async () => {
  delete process.env.GRAFIK_TERMINALI_ENABLED
  delete process.env.GRAFIK_PREVIEW_TOKEN
  assert.equal((await (await GET(istek())).json()).enabled, false)
})

test('FLAG: "0" disindaki hatali degerler de ACMAZ (yalnizca "1" acar)', async () => {
  delete process.env.GRAFIK_PREVIEW_TOKEN
  for (const deger of ['0', 'true', 'TRUE', 'evet', 'on', '2', '']) {
    process.env.GRAFIK_TERMINALI_ENABLED = deger
    const govde = await (await GET(istek())).json()
    assert.equal(govde.enabled, false, `"${deger}" acmamaliydi`)
  }
  delete process.env.GRAFIK_TERMINALI_ENABLED
})

test('FLAG: "1" acar', async () => {
  process.env.GRAFIK_TERMINALI_ENABLED = '1'
  assert.equal((await (await GET(istek())).json()).enabled, true)
  delete process.env.GRAFIK_TERMINALI_ENABLED
})

test('FLAG: ana bayrak kapaliyken DOGRU onizleme tokeni acar, yanlis olan ACMAZ', async () => {
  delete process.env.GRAFIK_TERMINALI_ENABLED
  process.env.GRAFIK_PREVIEW_TOKEN = 'gizli-grafik-tokeni'

  const dogru = await (await GET(istek('?grafik_preview=gizli-grafik-tokeni'))).json()
  assert.equal(dogru.enabled, true)
  assert.equal(dogru.onizleme_modu, true)

  const yanlis = await (await GET(istek('?grafik_preview=baska'))).json()
  assert.equal(yanlis.enabled, false)

  delete process.env.GRAFIK_PREVIEW_TOKEN
})

test('FLAG: token BOS DIZEYE AYARLIYKEN bos sorgu parametresi ACMAZ', async () => {
  // GERCEK RISK, mutasyon testiyle bulundu: .env dosyalarinda
  // `GRAFIK_PREVIEW_TOKEN=` (deger verilmeden) yazmak cok yaygindir. O zaman
  // degisken TANIMSIZ degil, BOS DIZE olur. `Boolean(onizlemeTokeni)` kapisi
  // olmasaydi `?grafik_preview=` istegi '' === '' ile ESLESIR ve bayrak
  // HERKESE ACILIRDI. Ilk yazdigim test degiskeni delete ediyordu; o durumda
  // undefined === '' zaten false oldugu icin kapiyi HIC SINAMIYORDU
  // (mutasyon hayatta kaldi).
  delete process.env.GRAFIK_TERMINALI_ENABLED
  process.env.GRAFIK_PREVIEW_TOKEN = ''
  assert.equal((await (await GET(istek('?grafik_preview='))).json()).enabled, false)
  assert.equal((await (await GET(istek())).json()).enabled, false)
  delete process.env.GRAFIK_PREVIEW_TOKEN
})

test('FLAG: token tanimsizken hicbir sorgu degeri ACMAZ', async () => {
  delete process.env.GRAFIK_TERMINALI_ENABLED
  delete process.env.GRAFIK_PREVIEW_TOKEN
  for (const sorgu of ['', '?grafik_preview=', '?grafik_preview=undefined', '?grafik_preview=null']) {
    assert.equal((await (await GET(istek(sorgu))).json()).enabled, false, `"${sorgu}" acmamaliydi`)
  }
})

test('FLAG: yanit onbelleklenmez (kill-switch saniyeler icinde etki etmeli)', async () => {
  delete process.env.GRAFIK_TERMINALI_ENABLED
  const res = await GET(istek())
  assert.equal(res.headers.get('Cache-Control'), 'no-store')
})
