// Kategori: RAPOR ROL KAPISI (İ-6)
//
// Ölçülen gerçek: bu belgelerde KULLANICI verisi yok (0 eşleşme), ama
// 33 servisin iç port envanteri ve KAPATILMAMIŞ güvenlik açıkları adıyla
// listeli. Bugün iki hesap da iç olduğu için fiilî sızıntı sıfır; ama
// db/migrations/004:58 yeni kullanıcıyı `role='user'` ile açıyor ve 005'teki
// tetik rolü hiç set etmiyor — yani ilk gerçek müşteri bunların tamamını
// indirebilirdi.
import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer, type Server } from 'node:http'
import { AddressInfo } from 'node:net'

const A = 'c59c7853-b752-44ca-b40d-c4eb09798b50'

let sunucu: Server
let sunulanRol: string | null = 'admin'
let rolSorgusuGeldi = false

let GET_LISTE: any, GET_DOSYA: any, NextRequest: any
let rolKarari: any, izinliRoller: any

before(async () => {
  sunucu = createServer((istek, yanit) => {
    const yol = istek.url || ''
    if (yol.startsWith('/auth/v1/user')) {
      yanit.writeHead(200, { 'content-type': 'application/json' })
      yanit.end(JSON.stringify({ id: A, aud: 'authenticated', role: 'authenticated' }))
      return
    }
    if (yol.includes('/rest/v1/profiles')) {
      rolSorgusuGeldi = true
      if (sunulanRol === null) {           // RLS/ağ hatası benzetimi
        yanit.writeHead(500, { 'content-type': 'application/json' })
        yanit.end(JSON.stringify({ message: 'hata' })); return
      }
      yanit.writeHead(200, { 'content-type': 'application/json' })
      yanit.end(JSON.stringify({ role: sunulanRol }))  // .single() tek nesne bekler
      return
    }
    yanit.writeHead(404); yanit.end('{}')
  })
  await new Promise<void>(c => sunucu.listen(0, '127.0.0.1', c))
  const taban = `http://127.0.0.1:${(sunucu.address() as AddressInfo).port}`

  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://sahtekimlik.local'
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon'
  process.env.SUPABASE_INTERNAL_URL = taban
  process.env.REPORTS_DIR = '/opt/alphawise/reports'

  GET_LISTE = (await import('../../src/app/api/raporlar/route')).GET
  GET_DOSYA = (await import('../../src/app/api/raporlar/[dosya]/route')).GET
  NextRequest = (await import('next/server')).NextRequest
  const r = await import('../../src/lib/raporlar')
  rolKarari = r.rolKarari; izinliRoller = (await import('../../src/lib/rol')).izinliRoller
})
after(() => { sunucu?.close() })

function gercekIstek(yol: string) {
  return new NextRequest(`http://localhost${yol}`, {
    headers: { cookie: `sb-sahtekimlik-auth-token=${cerez()}` },
  })
}
function cerez() {
  return 'base64-' + Buffer.from(JSON.stringify({
    access_token: 'jeton-A', refresh_token: 'y', expires_at: Math.floor(Date.now() / 1000) + 3600,
    token_type: 'bearer', user: { id: A },
  })).toString('base64')
}

// ------------------------------------------------- SAF KARAR (fail-closed)
test('KARAR: rol okunamadiysa (null) erisim REDDEDILIR — fail-closed', () => {
  assert.equal(rolKarari(null, ['admin', 'partner']), false)
})

test('KARAR: varsayilan rol "user" REDDEDILIR (ilk gercek musteri senaryosu)', () => {
  assert.equal(rolKarari('user', ['admin', 'partner']), false)
})

test('KARAR: admin ve partner GECER (bugunku iki hesap regresyona ugramaz)', () => {
  assert.equal(rolKarari('admin', ['admin', 'partner']), true)
  assert.equal(rolKarari('partner', ['admin', 'partner']), true)
})

test('KARAR: izin listesi daraltilinca partner REDDEDILIR', () => {
  assert.equal(rolKarari('partner', ['admin']), false)
  assert.equal(rolKarari('admin', ['admin']), true)
})

// ------------------------------------------------------------ izinliRoller
test('AYAR: bozuk/bos yapilandirma sessizce "herkese acik"a DONMEZ', () => {
  const v: any[] = ['admin']
  assert.deepEqual(izinliRoller('', v), v)
  assert.deepEqual(izinliRoller('   ', v), v)
  assert.deepEqual(izinliRoller('root,superuser', v), v, 'gecersiz roller varsayilana dusmeli')
  assert.deepEqual(izinliRoller(undefined, v), v)
})

test('AYAR: gecerli liste ayiklanir ve kucuk harfe indirilir', () => {
  assert.deepEqual(izinliRoller('ADMIN, partner', ['admin']), ['admin', 'partner'])
  assert.deepEqual(izinliRoller('admin,root', ['partner']), ['admin'])
})

// ------------------------------------------------------- UCTAN UCA: listeleme
test('UC: admin listeyi ALIR ve rol GERCEKTEN sorgulaniyor', async () => {
  sunulanRol = 'admin'
  rolSorgusuGeldi = false
  const y = await GET_LISTE(gercekIstek('/api/raporlar'))
  assert.equal(y.status, 200)
  const g = await y.json()
  assert.ok(Array.isArray(g.raporlar), 'rapor listesi donmeli')
  // Kapinin kisa devre yapmadiginin kaniti: rol sorgusu FIILEN yapildi.
  assert.equal(rolSorgusuGeldi, true, 'rol sorgulanmadan izin verilmis olamaz')
})

test('UC: rolu "user" olan kullanici 403 ALIR', async () => {
  sunulanRol = 'user'
  const y = await GET_LISTE(gercekIstek('/api/raporlar'))
  assert.equal(y.status, 403)
  const g = await y.json()
  assert.ok(!JSON.stringify(g).includes('gunsonu'), 'reddedilen cagiriya dosya adi sizmamali')
})

test('UC: rol okunamazsa 403 (fail-closed, uctan uca)', async () => {
  sunulanRol = null
  const y = await GET_LISTE(gercekIstek('/api/raporlar'))
  assert.equal(y.status, 403)
  assert.equal(y.headers.get('X-Rol'), 'okunamadi')
})

// --------------------------------------------------------- UCTAN UCA: indirme
test('UC: rolu "user" olan kullanici PDF INDIREMEZ', async () => {
  sunulanRol = 'user'
  const y = await GET_DOSYA(gercekIstek('/api/raporlar/x'), {
    params: Promise.resolve({ dosya: 'gunsonu_raporu_2026-08-21.pdf' }),
  })
  assert.equal(y.status, 403)
})

test('UC: admin PDF INDIREBILIR (regresyon yok)', async () => {
  sunulanRol = 'admin'
  const y = await GET_DOSYA(gercekIstek('/api/raporlar/x'), {
    params: Promise.resolve({ dosya: 'gunsonu_raporu_2026-08-21.pdf' }),
  })
  assert.equal(y.status, 200)
  assert.equal(y.headers.get('Content-Type'), 'application/pdf')
})

// -------------------------------------------- REGRESYON: yol asimi korumasi
test('REGRESYON: yol asimi hala engelleniyor (admin olsa bile)', async () => {
  sunulanRol = 'admin'
  for (const kotu of ['../../etc/passwd', '..%2F..%2Fetc%2Fpasswd', '.env', 'a/b.pdf']) {
    const y = await GET_DOSYA(gercekIstek('/api/raporlar/x'), {
      params: Promise.resolve({ dosya: kotu }),
    })
    assert.ok(y.status === 400 || y.status === 403, `${kotu} -> ${y.status}`)
  }
})

// ------------------------------------------------- SIZINTI: hata metni
test('SIZINTI: listeleme hatasinda ic yol kullaniciya gitmez', async () => {
  sunulanRol = 'admin'
  process.env.REPORTS_DIR = '/olmayan/gizli/yol/uzantisi'
  const yeni = (await import('../../src/app/api/raporlar/route?yeniden=1')).GET
  const y = await yeni(gercekIstek('/api/raporlar'))
  const metin = JSON.stringify(await y.json())
  assert.ok(!metin.includes('/olmayan/gizli'), `ic yol sizdi: ${metin}`)
  process.env.REPORTS_DIR = '/opt/alphawise/reports'
})
