// ============================================================================
// FAZ 3 — SIZINTI MATRİSİ (C4)
// ============================================================================
//
// 3.0 OTOMATİK SENARYO ÜRETİMİ: senaryolar ELLE yazılmaz. `src/app/api`
// ağacı taranır, her rota dosyasından bir URL üretilir ve HER rota için
// A→B erişim denemesi otomatik kurulur. Böylece "hangi ucu unuttum?"
// sorusu insana kalmaz; yeni bir rota eklendiği anda matrise girer.
//
// 3.2 GERÇEK ROL: testler middleware'i gerçek oturum çerezleriyle sürer;
// kimlik doğrulaması yerel bir saplama GoTrue'ya gider. Hiçbir yerde
// "kimliği varsayalım" kısayolu yoktur.
//
// NE KANITLANIR (Kapsam A sınırları içinde):
//   1. Her rotada A'nın isteği A kimliğini, B'ninki B kimliğini taşır.
//   2. Hiçbir rotada A'nın isteği B'nin kimliğini taşımaz.
//   3. A, kendini B gibi göstermeye çalışırsa ezilir (taklit koruması).
//   4. A'nın hız kovasını tüketmesi B'yi kilitlemez.
//   5. Kimliksiz istek hiçbir rotada aşağı akışa geçmez.
//
// NE KANITLANMAZ (ve neden): Kapsam A'da defter TEK SİSTEM HESABIDIR.
// Piyasa verisi uçları (DPKE, 13F, kongre, makro …) kullanıcıdan
// bağımsızdır ve paylaşılmaları TASARIMDIR, sızıntı değil. Matris bunu
// sınıflandırarak gösterir; "hepsi izole" gibi yanlış bir iddia kurmaz.
import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer, type Server } from 'node:http'
import { AddressInfo } from 'node:net'
import { readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const A = 'c59c7853-b752-44ca-b40d-c4eb09798b50'   // selcuk@alphawise.test
const B = 'd7e28a7c-d217-4abd-8fa5-ddc93d869d60'   // partner@alphawise.test
// ---------------------------------------------------------------------------
// SIRADAN BAGIMSIZLIK — her test KENDI kullanici ciftini acar.
// ---------------------------------------------------------------------------
// Hiz kovalari modul duzeyi durumdur ve ayni dosyadaki testler arasinda sizar.
// Matrisin her testi HER rotaya vurdugu icin (23 rota x 2 kullanici), birkac
// test sonra A ve B'nin kovalari kaciniamaz sekilde tukeniyor ve sondaki
// OLUMLU DENETIM 429 aliyordu - yani gercek bir kirilma degil, TEST SIRASI
// artefakti. Tek tek yamamak yerine her test kendi kullanicilariyla calisir;
// boylece dosya SIRADAN BAGIMSIZ olur ve yeni test eklemek eskisini bozmaz.
const JETON: Record<string, string> = { 'jeton-A': A, 'jeton-B': B }
let sayac = 0
/** Testin kendi kullanici ciftini uretir ve saplama sunucuya kaydeder. */
function taseKullanicilar(): [string, string, string, string] {
  const n = (++sayac).toString(16).padStart(2, '0')
  const u1 = `e${n}00000-0000-4000-8000-0000000000${n}`
  const u2 = `f${n}00000-0000-4000-8000-0000000000${n}`
  const j1 = `jeton-e${n}`, j2 = `jeton-f${n}`
  JETON[j1] = u1; JETON[j2] = u2
  return [j1, u1, j2, u2]
}

let sunucu: Server
let middleware: (req: any) => Promise<any>
let NextRequest: any
let KULLANICI_BASLIGI: string
let KIRACI_BASLIGI: string

// ---------------------------------------------------------------------------
// 3.0 — ROTA KEŞFİ (otomatik)
// ---------------------------------------------------------------------------
type Rota = { yol: string; dosya: string; sinif: 'KULLANICI' | 'PIYASA' | 'SISTEM' }

/** `src/app/api` ağacını gezip her route.ts için somut bir URL üretir. */
function rotalariKesfet(kok = 'src/app/api'): Rota[] {
  const bulunan: Rota[] = []
  const gez = (dizin: string, parcalar: string[]) => {
    for (const ad of readdirSync(dizin)) {
      const tam = join(dizin, ad)
      if (statSync(tam).isDirectory()) {
        // [ticker] → somut bir sembol; [...yol] → beyaz listedeki bir yol
        const parca = ad.startsWith('[...') ? 'memory/MSFT'
                    : ad.startsWith('[') ? (ad.includes('dosya') ? 'rapor.pdf' : 'MSFT')
                    : ad
        gez(tam, [...parcalar, parca])
      } else if (ad === 'route.ts') {
        const yol = '/api/' + parcalar.join('/')
        bulunan.push({ yol, dosya: tam, sinif: siniflandir(yol) })
      }
    }
  }
  gez(kok, [])
  return bulunan.sort((a, b) => a.yol.localeCompare(b.yol))
}

/**
 * Sınıflandırma — Kapsam A kararına göre.
 * KULLANICI : yanıtı kullanıcıya göre değişmesi GEREKEN uçlar
 * PIYASA    : kullanıcıdan bağımsız veri; paylaşım TASARIM
 * SISTEM    : sağlık/bayrak
 */
function siniflandir(yol: string): Rota['sinif'] {
  if (yol.startsWith('/api/raporlar')) return 'KULLANICI'   // rol kapısı var
  if (yol.startsWith('/api/portfoy')) return 'KULLANICI'    // defter (bugün sistem hesabı)
  if (yol.startsWith('/api/config')) return 'SISTEM'
  return 'PIYASA'
}

before(async () => {
  sunucu = createServer((istek, yanit) => {
    const yetki = String(istek.headers['authorization'] || '')
    const k = JETON[yetki.replace(/^Bearer\s+/i, '')]
    if (!k) { yanit.writeHead(401); yanit.end('{"error":"invalid"}'); return }
    yanit.writeHead(200, { 'content-type': 'application/json' })
    yanit.end(JSON.stringify({ id: k, aud: 'authenticated', role: 'authenticated' }))
  })
  await new Promise<void>(c => sunucu.listen(0, '127.0.0.1', c))
  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://sahtekimlik.local'
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon'
  process.env.SUPABASE_INTERNAL_URL = `http://127.0.0.1:${(sunucu.address() as AddressInfo).port}`

  middleware = (await import('../../src/middleware')).middleware as any
  NextRequest = (await import('next/server')).NextRequest
  const kk = await import('../../src/lib/kiraci')
  KULLANICI_BASLIGI = kk.KULLANICI_BASLIGI
  KIRACI_BASLIGI = kk.KIRACI_BASLIGI
})
after(() => { sunucu?.close() })

function cerez(jeton: string) {
  return 'base64-' + Buffer.from(JSON.stringify({
    access_token: jeton, refresh_token: 'y',
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    token_type: 'bearer', user: { id: JETON[jeton] },
  })).toString('base64')
}
function istek(yol: string, jeton?: string, ek: Record<string, string> = {}) {
  const b = new Headers(ek)
  if (jeton) b.set('cookie', `sb-sahtekimlik-auth-token=${cerez(jeton)}`)
  return new NextRequest(`http://localhost${yol}`, { headers: b })
}
const asagi = (y: any, ad: string) => y.headers.get(`x-middleware-request-${ad}`)

const ROTALAR = rotalariKesfet()

// ---------------------------------------------------------------------------
test('3.0 KEŞİF: matris rotaları otomatik buldu ve hiçbiri sınıfsız değil', () => {
  assert.ok(ROTALAR.length >= 20, `beklenenden az rota bulundu: ${ROTALAR.length}`)
  for (const r of ROTALAR) {
    assert.ok(['KULLANICI', 'PIYASA', 'SISTEM'].includes(r.sinif), `${r.yol} sinifsiz`)
  }
  // Matrisin kapsamı görünür olsun — "sessizce daraldı" diyemeyelim.
  const sayim = ROTALAR.reduce((a, r) => ((a[r.sinif] = (a[r.sinif] || 0) + 1), a), {} as any)
  console.log(`      [matris kapsami] ${ROTALAR.length} rota:`, JSON.stringify(sayim))
})

// ---------------------------------------------------------------------------
// 1 & 2 — her rotada kimlik doğru taşınıyor ve KARIŞMIYOR
// ---------------------------------------------------------------------------
test('MATRIS/1: HER rotada A kendi kimligini tasir, B kendi kimligini', async () => {
  const [j1, u1, j2, u2] = taseKullanicilar()
  const hatalar: string[] = []
  for (const r of ROTALAR) {
    const ya = await middleware(istek(r.yol, j1))
    const yb = await middleware(istek(r.yol, j2))
    // 403 (beyaz liste disi MAA yolu) disinda hepsi kimlik tasimali
    if (ya.status === 200 && asagi(ya, KULLANICI_BASLIGI) !== u1) {
      hatalar.push(`${r.yol}: 1. kullanici -> ${asagi(ya, KULLANICI_BASLIGI)}`)
    }
    if (yb.status === 200 && asagi(yb, KULLANICI_BASLIGI) !== u2) {
      hatalar.push(`${r.yol}: 2. kullanici -> ${asagi(yb, KULLANICI_BASLIGI)}`)
    }
  }
  assert.deepEqual(hatalar, [], `kimlik tasima hatalari:\n${hatalar.join('\n')}`)
})

test('MATRIS/2: HICBIR rotada A, B nin kimligini tasimaz (capraz bulasma yok)', async () => {
  const [j1, u1, , u2] = taseKullanicilar()
  const hatalar: string[] = []
  for (const r of ROTALAR) {
    const y = await middleware(istek(r.yol, j1))
    if (y.status === 200 && asagi(y, KULLANICI_BASLIGI) === u2) hatalar.push(r.yol)
    if (y.status === 200 && asagi(y, KULLANICI_BASLIGI) !== u1) hatalar.push(`${r.yol}: yabanci kimlik`)
  }
  assert.deepEqual(hatalar, [], `A istegi B kimligi tasidi: ${hatalar.join(', ')}`)
})

// ---------------------------------------------------------------------------
// 3 — TAKLİT: A kendini B gibi gösteremez (HER rotada)
// ---------------------------------------------------------------------------
test('MATRIS/3: HER rotada uydurma kimlik basligi EZILIR', async () => {
  const [j1, u1, , u2] = taseKullanicilar()
  const hatalar: string[] = []
  for (const r of ROTALAR) {
    const y = await middleware(istek(r.yol, j1, {
      [KULLANICI_BASLIGI]: u2, [KIRACI_BASLIGI]: 'kullanici',
    }))
    const gecen = asagi(y, KULLANICI_BASLIGI)
    if (y.status === 200 && gecen !== u1) hatalar.push(`${r.yol}: ${gecen}`)
    if (y.status !== 200 && gecen === u2) hatalar.push(`${r.yol}: red ama taklit gecti`)
  }
  assert.deepEqual(hatalar, [], `taklit basarili oldu:\n${hatalar.join('\n')}`)
})

// ---------------------------------------------------------------------------
// 5 — kimliksiz istek hicbir rotada asagi akisa gecmez
// ---------------------------------------------------------------------------
test('MATRIS/5: HER rotada kimliksiz istek 401 alir ve kimlik tasimaz', async () => {
  const hatalar: string[] = []
  for (const r of ROTALAR) {
    const y = await middleware(istek(r.yol))
    if (y.status !== 401) hatalar.push(`${r.yol}: ${y.status} (401 bekleniyordu)`)
    if (asagi(y, KULLANICI_BASLIGI)) hatalar.push(`${r.yol}: kimliksiz istek kimlik tasidi`)
  }
  assert.deepEqual(hatalar, [], `kimliksiz istek gecti:\n${hatalar.join('\n')}`)
})

// ---------------------------------------------------------------------------
// 4 — ADALET: A'nin kovasi B'yi kilitlemez (her SINIF icin)
// ---------------------------------------------------------------------------
test('MATRIS/4: bir kullanici kovasini tuketse bile DIGERI HER sinifta gecer', async () => {
  // Her hiz sinifindan bir temsilci: ucuz / sinyal / pahali.
  const temsilciler = [
    { yol: '/api/raporlar', sinif: 'ucuz', tavan: 40 },
    { yol: '/api/qlib/MSFT', sinif: 'sinyal', tavan: 45 },
    { yol: '/api/maa/narrative-verified/MSFT', sinif: 'pahali', tavan: 20 },
  ]
  for (const t of temsilciler) {
    const [j1, , j2, u2] = taseKullanicilar()
    let aDustu = false
    for (let i = 0; i < t.tavan; i++) {
      const y = await middleware(istek(t.yol, j1))
      if (y.status === 429) {
        assert.equal(y.headers.get('X-RateLimit-Asama'), 'kullanici',
          `${t.sinif}: C on kovadan dusmemeli`)
        aDustu = true; break
      }
    }
    assert.ok(aDustu, `${t.sinif}: C ${t.tavan} istekte kovasini tuketmeliydi`)
    const yd = await middleware(istek(t.yol, j2))
    assert.notEqual(yd.status, 429, `${t.sinif}: ikinci kullanici birincisi yuzunden kilitlendi`)
    assert.equal(asagi(yd, KULLANICI_BASLIGI), u2, `${t.sinif}: ikinci kimlik tasinmali`)
  }
})

// ---------------------------------------------------------------------------
// 3.3 — MEŞRU KULLANIM BOZULMADI
// ---------------------------------------------------------------------------
test('3.3 OLUMLU: mesru kullanim kirilmadi (kirilma varsa PAYLASILAN on kovadan)', async () => {
  const [j1, , j2] = taseKullanicilar()
  const piyasa = ROTALAR.filter(r => r.sinif === 'PIYASA')
  const gercekKirilma: string[] = []
  let onKovaRedleri = 0
  for (const r of piyasa) {
    for (const j of [j1, j2]) {
      const y = await middleware(istek(r.yol, j))
      if (y.status === 200 || y.status === 403) continue   // 403 = beyaz liste disi MAA
      if (y.status === 429 && y.headers.get('X-RateLimit-Asama') === 'on') {
        // PAYLASILAN on kova — bilincli tasarim, asagida ayrica olculuyor.
        onKovaRedleri++
        continue
      }
      gercekKirilma.push(`${r.yol} [${j}] -> ${y.status} (asama=${y.headers.get('X-RateLimit-Asama')})`)
    }
  }
  assert.deepEqual(gercekKirilma, [],
    `mesru kullanim KULLANICI kovasindan ya da baska bir nedenle kirildi:\n${gercekKirilma.join('\n')}`)
  console.log(`      [olumlu denetim] ${piyasa.length * 2} cagri; ` +
    `paylasilan on kovadan reddedilen: ${onKovaRedleri}`)
})

// ---------------------------------------------------------------------------
// BULGU — ON KOVA HALA PAYLASIMLI (bilincli odunlesme, ama sinir DEGIL)
// ---------------------------------------------------------------------------
// I-3 kullanici bazli kovayi getirdi ama ON KOVA (asama 1) hala ortak:
// anahtari `on:${istemciKimligi(req)}|${sinif}` ve istemciKimligi() guvenilir
// vekil yokken herkes icin 'ortak' donduruyor. Gerekcesi mesru: bu kovanin
// isi kredi paylastirmak DEGIL, Supabase dogrulama cagrisini selden korumak.
// Tavani sinif tavaninin 4 kati.
//
// SONUC (durustce): adalet MUTLAK DEGIL. Bir kullanici, kendi kovasinin 4
// katini asacak kadar yuklenirse ON KOVADAN digerlerini de 429'a dusurebilir.
// Bu test o siniri OLCER ve belgeler - gizlemez.
test('BULGU: on kova PAYLASIMLI - bir kullanici digerini yine de etkileyebilir', async () => {
  const [j1, , j2] = taseKullanicilar()
  const YOL = '/api/raporlar'          // 'ucuz': dakikada 120 / patlama 30
  // Tek kullanici 30'u asinca KENDI kovasindan duser; 30*4=120'yi asinca
  // ON KOVA da tukenir ve o noktadan sonra DIGER kullanici da etkilenir.
  let ilkKendiKovasi = 0, onKovayaGecis = 0
  for (let i = 0; i < 200; i++) {
    const y = await middleware(istek(YOL, j1))
    if (y.status === 429) {
      const asama = y.headers.get('X-RateLimit-Asama')
      if (asama === 'kullanici' && !ilkKendiKovasi) ilkKendiKovasi = i + 1
      if (asama === 'on') { onKovayaGecis = i + 1; break }
    }
  }
  assert.ok(ilkKendiKovasi > 0, 'once KENDI kovasindan dusmeliydi')
  assert.ok(onKovayaGecis > ilkKendiKovasi,
    'on kova kullanici kovasindan SONRA tukenmeli (4x pay)')
  // Ve o noktada ikinci kullanici da etkilenir - BU BEKLENEN DAVRANIS.
  const y2 = await middleware(istek(YOL, j2))
  const ikinciEtkilendi = y2.status === 429
  console.log(`      [on kova siniri] kendi kovasi ${ilkKendiKovasi}. istekte, ` +
    `on kova ${onKovayaGecis}. istekte doldu; ikinci kullanici etkilendi: ${ikinciEtkilendi}`)
  // DIKKAT: burada ORAN iddia EDILMEZ. Olculdu (17.09.2026): kendi kovasi 31.
  // istekte, on kova 92. istekte doldu - yani 4x degil ~3x. Sebep BULGUNUN
  // KENDISI: on kova PAYLASIMLI oldugu icin bu dosyadaki onceki testlerin
  // tuketimini de tasiyor, yani TAZE DEGIL. Bir orana baglamak, testi diger
  // testlerin sayisina bagimli kilar ve her yeni test eklendiginde kirar.
  // Anlamli ve kararli iddia SIRADIR: once kendi kovasi, SONRA on kova.
  assert.ok(onKovayaGecis > ilkKendiKovasi,
    `on kova, kullanici kovasindan ONCE tukendi (kendi=${ilkKendiKovasi} on=${onKovayaGecis}) ` +
    `- bu, kullanici bazli kovanin islevsiz oldugu anlamina gelir`)
  assert.equal(ikinciEtkilendi, true,
    'on kova dolduktan sonra ikinci kullanici da etkilenmeliydi - bu ODUNLESME belgelidir')
})
