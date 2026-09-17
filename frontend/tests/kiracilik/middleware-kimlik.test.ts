// Kategori: MIDDLEWARE KİMLİK TAŞIMA ve KULLANICI BAZLI KOVA (İ-1 / İ-3)
//
// Bu testler GERÇEK middleware'i çalıştırır; modül taklidi kullanılmaz.
// Supabase doğrulaması, SUPABASE_INTERNAL_URL yerel bir saplama sunucuya
// yönlendirilerek gerçek HTTP yolundan geçirilir — böylece "oturum geçerli"
// dalı da uçtan uca ölçülür, varsayılmaz.
import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer, type Server } from 'node:http'
import { AddressInfo } from 'node:net'

const A = 'c59c7853-b752-44ca-b40d-c4eb09798b50'
const B = 'd7e28a7c-d217-4abd-8fa5-ddc93d869d60'

let sunucu: Server
let taban: string
// Hangi erişim jetonu hangi kullanıcıya ait — saplama sunucu buna bakar.
const JETON_KULLANICI: Record<string, string> = { 'jeton-A': A, 'jeton-B': B }

let middleware: (req: any) => Promise<any>
let NextRequest: any
let KULLANICI_BASLIGI: string
let KIRACI_BASLIGI: string

before(async () => {
  sunucu = createServer((istek, yanit) => {
    // Supabase GoTrue'nun /auth/v1/user ucunu taklit eder.
    const yetki = istek.headers['authorization'] || ''
    const jeton = String(yetki).replace(/^Bearer\s+/i, '')
    const kullanici = JETON_KULLANICI[jeton]
    if (!kullanici) {
      yanit.writeHead(401, { 'content-type': 'application/json' })
      yanit.end(JSON.stringify({ error: 'invalid', error_description: 'bad token' }))
      return
    }
    yanit.writeHead(200, { 'content-type': 'application/json' })
    yanit.end(JSON.stringify({
      id: kullanici, aud: 'authenticated', role: 'authenticated',
      email: `${kullanici}@test.local`, app_metadata: {}, user_metadata: {},
      created_at: '2026-08-03T16:26:41Z',
    }))
  })
  await new Promise<void>(c => sunucu.listen(0, '127.0.0.1', c))
  taban = `http://127.0.0.1:${(sunucu.address() as AddressInfo).port}`

  // Ortam, modüller İÇE AKTARILMADAN ÖNCE kurulmalı: oturum.ts bu değerleri
  // modül düzeyinde bir kez okuyor.
  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://sahtekimlik.local'
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-anahtari'
  process.env.SUPABASE_INTERNAL_URL = taban

  const mw = await import('../../src/middleware')
  middleware = mw.middleware as any
  const ns = await import('next/server')
  NextRequest = ns.NextRequest
  const kk = await import('../../src/lib/kiraci')
  KULLANICI_BASLIGI = kk.KULLANICI_BASLIGI
  KIRACI_BASLIGI = kk.KIRACI_BASLIGI
})

after(() => { sunucu?.close() })

/** @supabase/ssr'in çerez biçimi: base64- öneki + JSON oturum. */
function oturumCerezi(jeton: string): string {
  const oturum = {
    access_token: jeton,
    refresh_token: `yenile-${jeton}`,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    expires_in: 3600,
    token_type: 'bearer',
    user: { id: JETON_KULLANICI[jeton] },
  }
  return 'base64-' + Buffer.from(JSON.stringify(oturum)).toString('base64')
}

function istek(yol: string, secenek: { jeton?: string; basliklar?: Record<string, string> } = {}) {
  const b = new Headers(secenek.basliklar ?? {})
  if (secenek.jeton) {
    b.set('cookie', `sb-sahtekimlik-auth-token=${oturumCerezi(secenek.jeton)}`)
  }
  return new NextRequest(`http://localhost${yol}`, { headers: b })
}

/** NextResponse.next({request:{headers}}) başlıkları bu şekilde kodlar. */
function asagiAkisBasligi(yanit: any, ad: string): string | null {
  return yanit.headers.get(`x-middleware-request-${ad}`)
}

// ---------------------------------------------------------------- 401 yolu
test('KIMLIK: cerez yoksa 401 ve HICBIR kimlik basligi asagi gitmez', async () => {
  const y = await middleware(istek('/api/raporlar'))
  assert.equal(y.status, 401)
  assert.equal(y.headers.get('X-Oturum'), 'cerez_yok')
})

test('KIMLIK: gecersiz jeton 401 alir (saplama sunucu reddediyor)', async () => {
  const y = await middleware(istek('/api/raporlar', { jeton: 'jeton-YOK' }))
  assert.equal(y.status, 401)
})

// ------------------------------------------------------- kimlik tasima (I-1)
test('I-1: gecerli oturumda kullanici kimligi ASAGI AKISA tasinir', async () => {
  const y = await middleware(istek('/api/raporlar', { jeton: 'jeton-A' }))
  assert.equal(y.status, 200)
  assert.equal(asagiAkisBasligi(y, KULLANICI_BASLIGI), A)
  assert.equal(asagiAkisBasligi(y, KIRACI_BASLIGI), 'kullanici')
})

test('I-1: farkli kullanici FARKLI kimlik tasir (karismiyor)', async () => {
  const ya = await middleware(istek('/api/raporlar', { jeton: 'jeton-A' }))
  const yb = await middleware(istek('/api/raporlar', { jeton: 'jeton-B' }))
  assert.equal(asagiAkisBasligi(ya, KULLANICI_BASLIGI), A)
  assert.equal(asagiAkisBasligi(yb, KULLANICI_BASLIGI), B)
  assert.notEqual(
    asagiAkisBasligi(ya, KULLANICI_BASLIGI),
    asagiAkisBasligi(yb, KULLANICI_BASLIGI),
  )
})

// --------------------------------------------------------- TAKLIT KORUMASI
test('TAKLIT: istemcinin uydurdugu kimlik basligi EZILIR', async () => {
  // A giris yapmis ama kendini B gibi gostermeye calisiyor.
  const y = await middleware(istek('/api/raporlar', {
    jeton: 'jeton-A',
    basliklar: { [KULLANICI_BASLIGI]: B, [KIRACI_BASLIGI]: 'kullanici' },
  }))
  assert.equal(y.status, 200)
  assert.equal(asagiAkisBasligi(y, KULLANICI_BASLIGI), A, 'A, B gibi gorunememeli')
})

test('TAKLIT: sinifi olmayan yolda bile uydurma baslik TEMIZLENIR', async () => {
  // '/api' tam yolu sinifBelirle()'den null alir ve tum kontrolleri atlar.
  // Bu dalda bile istemcinin basligi asagi akisa GECMEMELI.
  const y = await middleware(istek('/api', {
    basliklar: { [KULLANICI_BASLIGI]: B, [KIRACI_BASLIGI]: 'kullanici' },
  }))
  const gecen = asagiAkisBasligi(y, KULLANICI_BASLIGI)
  assert.ok(gecen === null || gecen === '', `uydurma kimlik gecti: ${gecen}`)
})

// ------------------------------------------------- MAA beyaz listesi korundu
test('REGRESYON: beyaz liste disi MAA yolu hala 403 (jeton harcamadan)', async () => {
  const y = await middleware(istek('/api/maa/decide/MSFT', { jeton: 'jeton-A' }))
  assert.equal(y.status, 403)
})

test('REGRESYON: beyaz listedeki MAA yolu gecer', async () => {
  const y = await middleware(istek('/api/maa/memory/MSFT', { jeton: 'jeton-A' }))
  assert.equal(y.status, 200)
})

// ------------------------------------------------------ hiz siniri baslıkları
test('I-3: basarili istekte hiz siniri basliklari hala bildiriliyor', async () => {
  const y = await middleware(istek('/api/raporlar', { jeton: 'jeton-A' }))
  assert.equal(y.headers.get('X-RateLimit-Sinif'), 'ucuz')
  assert.ok(Number(y.headers.get('X-RateLimit-Limit')) > 0)
  assert.ok(y.headers.get('X-RateLimit-Remaining') !== null)
})

// ================================================================= İ-3 ADALET
// Asil iddia: "A'nin 429'u B'yi ETKILEMEZ." Bugunku kod tek 'ortak' kova
// kullandigi icin bu iddia FAZ 2 ONCESI YANLISTI.
//
// KREDI HARCAMAZ: 'ucuz' sinifi (/api/raporlar, dakikada 120 / patlama 30)
// kullanilir. Kova mantigi izinVar() icinde SINIFTAN BAGIMSIZDIR; hangi
// sinifla dogrulandigi onemsizdir, tek fark tavana ulasmak icin gereken
// istek sayisidir. 'pahali' sinifiyla dogrulamak ayni gucte olurdu ama her
// istek OpenRouter kredisi yakardi.
test('I-3 ADALET: A kendi kovasini tuketse bile B etkilenmez', async () => {
  // 'ucuz' patlama tavani 30; on kova tavani 30 x ON_KOVA_CARPANI(4) = 120.
  // 40 istek A'nin kovasini bitirir ama on kovayi (120) bitirmez.
  let aSonDurum = 200
  for (let i = 0; i < 40; i++) {
    const y = await middleware(istek('/api/raporlar', { jeton: 'jeton-A' }))
    aSonDurum = y.status
    if (y.status === 429) {
      assert.equal(y.headers.get('X-RateLimit-Asama'), 'kullanici',
        'A kullanici kovasindan dusmeli, on kovadan DEGIL')
      break
    }
  }
  assert.equal(aSonDurum, 429, 'A 40 istekte kendi kovasini tuketmeliydi')

  // B'nin istegi GECMELI - kovalar ayri.
  const yb = await middleware(istek('/api/raporlar', { jeton: 'jeton-B' }))
  assert.equal(yb.status, 200, 'B, A yuzunden kilitlenmemeli')
  assert.equal(asagiAkisBasligi(yb, KULLANICI_BASLIGI), B)
})
