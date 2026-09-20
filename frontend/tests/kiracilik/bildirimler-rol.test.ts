// Kategori: BILDIRIM MERKEZI ROL KAPISI (R-9)
//
// OLCULEN GERCEK (20.09.2026, canli /bildirimler yaniti):
// Besleme capraz-kullanici verisi TASIMIYOR — icerik her kullanici icin ayni.
// Ama zararsiz da degil; donen satirlar sistemin isletim mimarisini aciga
// veriyor:
//   "[ana:claude1] ALARM: claude CALISMIYOR (pane_pid=3960990).
//    Yeniden baslatiliyor: 'claude --continue' (ardisik deneme: 1/6)"
//   godmode_paper "MUTABAKAT ALARMI: Kontrol calistirilamadi ..."
// Yani otomasyonun tmux'ta yeniden baslatilan Claude oturumlariyla yurudugu,
// surec kimlikleri ve ic saglik durumu. Sinif: SISTEM-GIZLI (raporlar ucuyla
// ayni sinif), KULLANICI-GIZLI degil.
//
// Bu yuzden dogru cozum kullanici bazli bolme DEGIL, rol kapisidir.
import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer, type Server } from 'node:http'
import { AddressInfo } from 'node:net'

const A = 'c59c7853-b752-44ca-b40d-c4eb09798b50'

// Gercek beslemeden alinmis, SIZMAMASI gereken ornek satir.
const SIZMAMASI_GEREKEN =
  "[ana:claude1] ALARM: claude CALISMIYOR (pane_pid=3960990). " +
  "Yeniden baslatiliyor: 'claude --continue'"

let kimlikSunucu: Server
let bildirimSunucu: Server
let sunulanRol: string | null = 'admin'
let rolSorgusuGeldi = false
let asagiAkisCagrildi = false

let GET: any, NextRequest: any

before(async () => {
  kimlikSunucu = createServer((istek, yanit) => {
    const yol = istek.url || ''
    if (yol.startsWith('/auth/v1/user')) {
      yanit.writeHead(200, { 'content-type': 'application/json' })
      yanit.end(JSON.stringify({ id: A, aud: 'authenticated', role: 'authenticated' }))
      return
    }
    if (yol.includes('/rest/v1/profiles')) {
      rolSorgusuGeldi = true
      if (sunulanRol === null) {
        yanit.writeHead(500, { 'content-type': 'application/json' })
        yanit.end(JSON.stringify({ message: 'hata' })); return
      }
      yanit.writeHead(200, { 'content-type': 'application/json' })
      yanit.end(JSON.stringify({ role: sunulanRol }))
      return
    }
    yanit.writeHead(404); yanit.end('{}')
  })
  await new Promise<void>(c => kimlikSunucu.listen(0, '127.0.0.1', c))

  // Asagi akis bildirim servisi saplamasi: GERCEK sizinti metnini dondurur,
  // boylece "kapi calisiyor" iddiasi icerik uzerinden dogrulanabilir.
  bildirimSunucu = createServer((_istek, yanit) => {
    asagiAkisCagrildi = true
    yanit.writeHead(200, { 'content-type': 'application/json' })
    yanit.end(JSON.stringify({
      ozet: { alarm: 1 },
      bildirimler: [{ kaynak: 'otonom_bekci', duzey: 'alarm', mesaj: SIZMAMASI_GEREKEN }],
    }))
  })
  await new Promise<void>(c => bildirimSunucu.listen(0, '127.0.0.1', c))

  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://sahtekimlik.local'
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon'
  process.env.SUPABASE_INTERNAL_URL =
    `http://127.0.0.1:${(kimlikSunucu.address() as AddressInfo).port}`
  process.env.BILDIRIM_URL =
    `http://127.0.0.1:${(bildirimSunucu.address() as AddressInfo).port}`
  delete process.env.BILDIRIM_IZINLI_ROLLER

  GET = (await import('../../src/app/api/bildirimler/route')).GET
  NextRequest = (await import('next/server')).NextRequest
})

after(() => { kimlikSunucu?.close(); bildirimSunucu?.close() })

function cerez() {
  return 'base64-' + Buffer.from(JSON.stringify({
    access_token: 'jeton-A', refresh_token: 'y',
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    token_type: 'bearer', user: { id: A },
  })).toString('base64')
}
function gercekIstek() {
  return new NextRequest('http://localhost/api/bildirimler', {
    headers: { cookie: `sb-sahtekimlik-auth-token=${cerez()}` },
  })
}

// --------------------------------------------------------------- REDDEDILEN
test('UC: rolu "user" olan kullanici 403 ALIR', async () => {
  sunulanRol = 'user'
  const y = await GET(gercekIstek())
  assert.equal(y.status, 403)
})

test('KAPI ASAGI AKISTAN ONCE: yetkisiz cagri servise HIC ULASMAZ', async () => {
  // Asil iddia bu. Kapi proxy'den SONRA olsaydi yanit gizlenir ama istek
  // yine de gider; hem zamanlama bilgi sizdirir hem de asagi akis servisi
  // yetkisiz trafigi gorur.
  sunulanRol = 'user'
  asagiAkisCagrildi = false
  const y = await GET(gercekIstek())
  assert.equal(y.status, 403)
  assert.equal(asagiAkisCagrildi, false, 'yetkisiz istek asagi akisa gitti')
})

test('SIZINTI: 403 govdesinde isletim ayrintisi YOK', async () => {
  sunulanRol = 'user'
  const y = await GET(gercekIstek())
  const govde = JSON.stringify(await y.json())
  for (const iz of ['claude', 'pane_pid', 'tmux', 'ALARM', 'otonom_bekci', 'godmode']) {
    assert.ok(!govde.includes(iz), `reddedilen cagiriya "${iz}" sizdi: ${govde}`)
  }
})

test('UC: rol okunamazsa 403 (fail-closed) ve asagi akis cagrilmaz', async () => {
  sunulanRol = null
  asagiAkisCagrildi = false
  const y = await GET(gercekIstek())
  assert.equal(y.status, 403)
  assert.equal(y.headers.get('X-Rol'), 'okunamadi')
  assert.equal(asagiAkisCagrildi, false)
})

// ------------------------------------------------------------ REGRESYON YOK
test('UC: admin beslemeyi ALIR ve rol GERCEKTEN sorgulaniyor', async () => {
  sunulanRol = 'admin'
  rolSorgusuGeldi = false
  asagiAkisCagrildi = false
  const y = await GET(gercekIstek())
  assert.equal(y.status, 200)
  assert.equal(rolSorgusuGeldi, true, 'rol sorgulanmadan izin verilmis olamaz')
  assert.equal(asagiAkisCagrildi, true, 'yetkili cagri asagi akisa ulasmaliydi')
  const g = await y.json()
  assert.ok(JSON.stringify(g).includes('pane_pid'),
    'yetkili cagiran beslemenin kendisini almali (kapi icerik BOZMAMALI)')
})

test('UC: partner de ALIR (bugunku iki hesap regresyona ugramaz)', async () => {
  sunulanRol = 'partner'
  const y = await GET(gercekIstek())
  assert.equal(y.status, 200)
})

// ----------------------------------------------------------------- AYAR
test('AYAR: BILDIRIM_IZINLI_ROLLER=admin ise partner REDDEDILIR', async () => {
  process.env.BILDIRIM_IZINLI_ROLLER = 'admin'
  try {
    sunulanRol = 'partner'
    assert.equal((await GET(gercekIstek())).status, 403)
    sunulanRol = 'admin'
    assert.equal((await GET(gercekIstek())).status, 200)
  } finally {
    delete process.env.BILDIRIM_IZINLI_ROLLER
  }
})

test('AYAR: bozuk yapilandirma sessizce "herkese acik"a DONMEZ', async () => {
  process.env.BILDIRIM_IZINLI_ROLLER = 'root,superuser'   // hicbiri gecerli degil
  try {
    sunulanRol = 'user'
    assert.equal((await GET(gercekIstek())).status, 403,
      'gecersiz rol listesi varsayilana dusmeli, herkese acilmamali')
  } finally {
    delete process.env.BILDIRIM_IZINLI_ROLLER
  }
})
