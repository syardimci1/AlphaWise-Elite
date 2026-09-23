// Kategori: KİMLİK UCU — grafik çizimlerinin localStorage ad alanı için
// çağıranın KENDİ kimliğini döndürür (ADR-2). Kiracı izolasyonu bu depoda
// sert bir ilkedir, o yüzden bu uç ayrıca test edilir.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { NextRequest } from 'next/server'
import { GET } from '../../src/app/api/config/kimlik/route'
import { KULLANICI_BASLIGI, KIRACI_BASLIGI } from '../../src/lib/kiraci'

const KIMLIK_A = '11111111-1111-4111-8111-111111111111'
const KIMLIK_B = '22222222-2222-4222-8222-222222222222'

function istek(basliklar: Record<string, string>): NextRequest {
  return new NextRequest('http://localhost/api/config/kimlik', { headers: basliklar })
}

test('KİMLİK: başlıksız istek 401 döner, boş kimlik UYDURMAZ', async () => {
  const res = await GET(istek({}))
  assert.equal(res.status, 401)
  const govde = await res.json()
  assert.equal(govde.kullaniciId, undefined)
})

test('KİMLİK: çağıranın KENDİ kimliği döner', async () => {
  const res = await GET(istek({ [KULLANICI_BASLIGI]: KIMLIK_A, [KIRACI_BASLIGI]: 'kullanici' }))
  assert.equal(res.status, 200)
  const govde = await res.json()
  assert.equal(govde.kullaniciId, KIMLIK_A)
  assert.equal(govde.kiraci, 'kullanici')
})

test('KİMLİK: iki farklı kullanıcı FARKLI kimlik alır (ad alanı gerçekten ayrışır)', async () => {
  const a = await (await GET(istek({ [KULLANICI_BASLIGI]: KIMLIK_A, [KIRACI_BASLIGI]: 'kullanici' }))).json()
  const b = await (await GET(istek({ [KULLANICI_BASLIGI]: KIMLIK_B, [KIRACI_BASLIGI]: 'kullanici' }))).json()
  assert.notEqual(a.kullaniciId, b.kullaniciId)
})

test('KİMLİK: geçersiz biçimli kimlik kabul EDİLMEZ', async () => {
  // kiraci.ts kimlikDogrula UUID ya da 'sistem' bekler; uydurma bir değer
  // localStorage ad alanına sızmamalı.
  const res = await GET(istek({ [KULLANICI_BASLIGI]: '../../etc/passwd', [KIRACI_BASLIGI]: 'kullanici' }))
  assert.equal(res.status, 401)
})

test('KİMLİK: yanıt önbelleklenmez (oturum değişince bayat kimlik dönmemeli)', async () => {
  const res = await GET(istek({ [KULLANICI_BASLIGI]: KIMLIK_A, [KIRACI_BASLIGI]: 'kullanici' }))
  assert.equal(res.headers.get('Cache-Control'), 'no-store')
})
