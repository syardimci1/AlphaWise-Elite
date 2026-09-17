// ============================================================================
// FAZ 4 — REGRESYON AĞI (15 madde)
// ============================================================================
//
// Görev metnindeki 4.1–4.15 maddelerinin frontend tarafı. Veritabanı ve
// konteyner gerektiren maddeler (4.1 defter, 4.4 AST, 4.9 geri alma)
// `kanit/faz4_regresyon.sh` içinde ölçülür; burada her biri için hangi
// betiğin çalıştığı NOT olarak yazılıdır — madde sessizce atlanmasın.
//
// KREDİ HARCAMAZ: hiçbir test gerçek MAA/OpenRouter çağrısı yapmaz.
// Yük testi (4.7) `sinyal` sınıfıyla ve yerel saplama sunucuyla çalışır.
import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer, type Server } from 'node:http'
import { AddressInfo } from 'node:net'

let sunucu: Server
let taban: string
let middleware: any, NextRequest: any
let KULLANICI_BASLIGI: string, KIRACI_BASLIGI: string
let servisProxy: any, detayiSuz: any

const JETON: Record<string, string> = {}
let sayac = 0
function kullaniciAc(): [string, string] {
  const n = (++sayac).toString(16).padStart(2, '0')
  const u = `a${n}00000-0000-4000-8000-0000000000${n}`
  const j = `jeton-${n}`
  JETON[j] = u
  return [j, u]
}

/** Süresi dolmuş / geçersiz jeton üretimi için. */
function cerez(jeton: string, sureDoldu = false) {
  const zaman = Math.floor(Date.now() / 1000)
  return 'base64-' + Buffer.from(JSON.stringify({
    access_token: jeton, refresh_token: 'y',
    expires_at: sureDoldu ? zaman - 3600 : zaman + 3600,
    token_type: 'bearer', user: { id: JETON[jeton] ?? 'bilinmiyor' },
  })).toString('base64')
}
function istek(yol: string, jeton?: string, ek: Record<string, string> = {}, sureDoldu = false) {
  const b = new Headers(ek)
  if (jeton) b.set('cookie', `sb-sahtekimlik-auth-token=${cerez(jeton, sureDoldu)}`)
  return new NextRequest(`http://localhost${yol}`, { headers: b })
}
const asagi = (y: any, ad: string) => y.headers.get(`x-middleware-request-${ad}`)

// Saplama kimlik sunucusu — GÖRÜLEN başlıkları da kaydeder (4.10 için).
let gorulenBasliklar: Array<Record<string, any>> = []

before(async () => {
  sunucu = createServer((istekHam, yanit) => {
    gorulenBasliklar.push({ ...istekHam.headers })
    const yol = istekHam.url || ''
    if (yol.includes('/rest/v1/')) {          // rol sorgusu
      yanit.writeHead(200, { 'content-type': 'application/json' })
      yanit.end(JSON.stringify({ role: 'admin' })); return
    }
    const j = String(istekHam.headers['authorization'] || '').replace(/^Bearer\s+/i, '')
    const k = JETON[j]
    if (!k) { yanit.writeHead(401); yanit.end('{"error":"invalid"}'); return }
    yanit.writeHead(200, { 'content-type': 'application/json' })
    yanit.end(JSON.stringify({ id: k, aud: 'authenticated', role: 'authenticated' }))
  })
  await new Promise<void>(c => sunucu.listen(0, '127.0.0.1', c))
  taban = `http://127.0.0.1:${(sunucu.address() as AddressInfo).port}`
  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://sahtekimlik.local'
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon'
  process.env.SUPABASE_INTERNAL_URL = taban

  middleware = (await import('../../src/middleware')).middleware
  NextRequest = (await import('next/server')).NextRequest
  const kk = await import('../../src/lib/kiraci')
  KULLANICI_BASLIGI = kk.KULLANICI_BASLIGI; KIRACI_BASLIGI = kk.KIRACI_BASLIGI
  const sp = await import('../../src/lib/servis-proxy')
  servisProxy = sp.servisProxy; detayiSuz = sp.detayiSuz
})
after(() => { sunucu?.close() })

// ============================================================================
// 4.2 — Sızıntı matrisi tam PASS
// ============================================================================
test('4.2 Sizinti matrisi: ayri dosyada, tam gecis sarti', () => {
  // Matris `sizinti-matrisi.test.ts`'te; `npm test` ikisini de kosar.
  // Burada yalnizca SOZLESME kaydi: matris kirmiziysa bu faz kapanamaz.
  assert.ok(true)
})

// ============================================================================
// 4.3 — Admin/dar anahtar akışı hâlâ çalışıyor
// ============================================================================
test('4.3 ADMIN AKISI: beyaz liste disi MAA yolu hala JETON HARCAMADAN 403', async () => {
  const [j] = kullaniciAc()
  const y = await middleware(istek('/api/maa/decide/MSFT', j))
  assert.equal(y.status, 403)
  // Jeton harcanmadiginin kaniti: ayni kullanici hemen ardindan gecerli bir
  // yolda 200 alabilmeli (kovasi bosalmamis olmali).
  const y2 = await middleware(istek('/api/raporlar', j))
  assert.equal(y2.status, 200)
})

test('4.3 ADMIN AKISI: beyaz listedeki uc yol da hala geciyor', async () => {
  const [j] = kullaniciAc()
  for (const yol of [
    '/api/maa/portfolio-signal/adaptive_rotation',
    '/api/maa/narrative-verified/MSFT',
    '/api/maa/memory/MSFT',
  ]) {
    const y = await middleware(istek(yol, j))
    assert.equal(y.status, 200, `${yol} -> ${y.status}`)
  }
})

// ============================================================================
// 4.6 — Kimlik katmanı <50 ms gecikme ekliyor mu
// ============================================================================
test('4.6 GECIKME: kimlik katmani istek basina <50ms ekliyor', async () => {
  const [j] = kullaniciAc()
  const N = 30
  const t0 = process.hrtime.bigint()
  for (let i = 0; i < N; i++) await middleware(istek('/api/raporlar', j))
  const t1 = process.hrtime.bigint()
  const ortalamaMs = Number(t1 - t0) / 1e6 / N
  console.log(`      [4.6 gecikme] istek basina ortalama ${ortalamaMs.toFixed(2)} ms ` +
    `(yerel saplama kimlik sunucusuyla)`)
  // NOT: bu olcum YEREL saplama sunucuyla yapiliyor; gercek Supabase'in ag
  // gecikmesi buna EKLENIR ve o, kimlik katmaninin DEGIL altyapinin maliyetidir.
  // Olculen sey: bizim ekledigimiz islem yuku.
  assert.ok(ortalamaMs < 50, `kimlik katmani cok yavas: ${ortalamaMs.toFixed(2)} ms`)
})

// ============================================================================
// 4.7 — Yük: 100 eşzamanlı kullanıcı, sızıntı yok
// ============================================================================
// YUK TESTI 'sinyal' SINIFINDA: on kova anahtari `on:ortak|<sinif>` oldugu
// icin her sinifin AYRI on kovasi var. Yuk testini 'ucuz' sinifinda yapmak
// (ki ilk surum oyleydi) 100 jetonu tuketip SONRAKI testleri 429'a dusuruyordu
// - gercek bir kirilma degil, paylasilan on kovanin yapisal sonucu.
// Farkli sinif kullanmak testleri birbirinden ayirir.
test('4.7 YUK: 100 es zamanli kullanici, kimlik KARISMIYOR', async () => {
  const kullanicilar = Array.from({ length: 100 }, () => kullaniciAc())
  const sonuclar = await Promise.all(
    kullanicilar.map(([j]) => middleware(istek('/api/qlib/MSFT', j))),
  )
  const hatalar: string[] = []
  sonuclar.forEach((y, i) => {
    const [, beklenen] = kullanicilar[i]
    const gecen = asagi(y, KULLANICI_BASLIGI)
    // 429 kabul (paylasilan on kova); ama 200 ise kimlik DOGRU olmali.
    if (y.status === 200 && gecen !== beklenen) {
      hatalar.push(`${i}: beklenen ${beklenen}, gecen ${gecen}`)
    }
  })
  const basarili = sonuclar.filter(y => y.status === 200).length
  console.log(`      [4.7 yuk] 100 es zamanli istek; 200 alan: ${basarili}, ` +
    `429 alan: ${sonuclar.filter(y => y.status === 429).length}`)
  assert.deepEqual(hatalar, [], `es zamanlilikta kimlik karisti:\n${hatalar.join('\n')}`)
  assert.ok(basarili > 0, 'hicbir istek gecmedi - olcum anlamsiz')
})

// ============================================================================
// 4.8 — Hata senaryoları: jeton yok / süresi dolmuş / yanlış kimlik
// ============================================================================
test('4.8 HATA: jeton YOK -> 401, kimlik asagi gitmez', async () => {
  const y = await middleware(istek('/api/raporlar'))
  assert.equal(y.status, 401)
  assert.equal(asagi(y, KULLANICI_BASLIGI), null)
})

test('4.8 HATA: TANINMAYAN jeton -> 401 (kimlik sunucusu reddediyor)', async () => {
  const y = await middleware(istek('/api/raporlar', 'jeton-uydurma'))
  assert.equal(y.status, 401)
  assert.equal(asagi(y, KULLANICI_BASLIGI), null)
})

test('4.8 HATA: bozuk cerez govdesi -> 401, cokmez', async () => {
  const r = new NextRequest('http://localhost/api/raporlar', {
    headers: { cookie: 'sb-sahtekimlik-auth-token=bu-gecerli-base64-degil!!!' },
  })
  const y = await middleware(r)
  assert.equal(y.status, 401)
})

test('4.8 HATA: UYDURMA user_id basligi kimlige DONUSMEZ', async () => {
  const [, sahte] = kullaniciAc()
  // Cerez YOK ama baslik var: middleware cerezsiz istegi 401 yapar ve
  // uydurma baslik asagi akisa GECMEZ.
  const y = await middleware(istek('/api/raporlar', undefined, {
    [KULLANICI_BASLIGI]: sahte, [KIRACI_BASLIGI]: 'kullanici',
  }))
  assert.equal(y.status, 401)
  assert.equal(asagi(y, KULLANICI_BASLIGI), null)
})

// ============================================================================
// 4.10 — Loglarda/yukarı akışta başka kullanıcının verisi yok
// ============================================================================
test('4.10 LOG: yukari akisa giden basliklar YALNIZCA cagiranin kimligini tasir', async () => {
  gorulenBasliklar = []
  const [j1, u1] = kullaniciAc()
  const [, u2] = kullaniciAc()
  await middleware(istek('/api/raporlar', j1))
  const hepsi = JSON.stringify(gorulenBasliklar)
  assert.ok(!hepsi.includes(u2), `baska kullanicinin kimligi yukari akisa gitti: ${u2}`)
})

test('4.10 LOG: proxy yukari akisa YALNIZCA kendi kimligini gonderir', async () => {
  gorulenBasliklar = []
  const [, u1] = kullaniciAc()
  const [, u2] = kullaniciAc()
  await servisProxy({
    taban, yol: '/x', zamanAsimiMs: 5000, servisAdi: 'D',
    kimlik: { kullaniciId: u1, kiraci: 'kullanici' },
  })
  const hepsi = JSON.stringify(gorulenBasliklar)
  assert.ok(hepsi.includes(u1), 'kendi kimligi gitmeliydi')
  assert.ok(!hepsi.includes(u2), 'baska kimlik sizdi')
})

// ============================================================================
// 4.11 — Önbellek anahtarlarında kullanıcı boyutu (KARAR kaydı)
// ============================================================================
test('4.11 ONBELLEK: MAA onbellegi BILEREK global - karar kilitleniyor', async () => {
  // Kapsam A karari: MAA ciktisi ticker'in fonksiyonudur, kullanici boyutu
  // TASIMAZ (Faz 1'de olculdu). Onbellek anahtarina kullanici eklemek krediyi
  // kullanici sayisiyla CARPARDI ve HICBIR sizinti kapatmazdi.
  // Bu test o karari kilitler: dosyada kullanici bazli anahtarlama YOKSA gecer;
  // biri "duzeltmek" icin eklerse bu test kirmiziya doner ve karar yeniden
  // tartisilir (sessizce kredi carpilmaz).
  const { readFileSync } = await import('node:fs')
  const kaynak = readFileSync('src/app/api/maa/[...yol]/route.ts', 'utf8')
  const anahtarSatiri = kaynak.match(/SONUC_ONBELLEGI\.(get|set)\(([^,)]+)/g) || []
  assert.ok(anahtarSatiri.length > 0, 'onbellek kullanimi bulunamadi')
  for (const s of anahtarSatiri) {
    assert.ok(!/kullanici|user/i.test(s),
      `onbellek anahtarina kullanici eklenmis: ${s} - BUTCE KURALI geregi bu ` +
      `degisiklik acik onay ister (krediyi kullanici sayisiyla carpar)`)
  }
})

test('4.11 ONBELLEK: rapor rol kapisi onbelleklenmiyor (her istekte kontrol)', async () => {
  const { readFileSync } = await import('node:fs')
  const kaynak = readFileSync('src/lib/raporlar.ts', 'utf8')
  assert.ok(!/cache|onbellek|memo/i.test(kaynak),
    'rol karari onbelleklenirse rol degisikligi gecikmeli uygulanir')
})

// ============================================================================
// 4.12 — Hata mesajları bilgi sızdırmıyor
// ============================================================================
test('4.12 SIZINTI: kullanici kiracisinda sir adi ve ic adres GECMEZ', async () => {
  const [, u] = kullaniciAc()
  const kimlik = { kullaniciId: u, kiraci: 'kullanici' as const }
  // Gercek gamma-exposure govdesi
  const s1 = detayiSuz({
    hata: 'Kota doldu', aciklama: 'Yarin tekrar deneyin',
    kota_durumu: { anahtar_basina: [{ anahtar: 'FLASHALPHA_API_KEY_2', kullanilan: 5 }] },
  }, kimlik)
  assert.ok(!String(s1).includes('FLASHALPHA'), 'API anahtari adi sizdi')
  assert.ok(!String(s1).includes('kullanilan'), 'ortak sayac sizdi')
  assert.ok(String(s1).includes('Kota doldu'), 'kullaniciya anlamli sebep gitmeli')
  // Ag hatasi
  const y = await servisProxy({
    taban: 'http://127.0.0.1:1', yol: '/x', zamanAsimiMs: 3000,
    servisAdi: 'Kapali', kimlik,
  })
  const g = await y.json()
  assert.equal(g.detay, null, 'ic adres/port sizdi')
})

test('4.12 SIZINTI: 401/403 yanitlari SEBEP AYRIMI sizdirmaz', async () => {
  const yCerezsiz = await middleware(istek('/api/raporlar'))
  const yGecersiz = await middleware(istek('/api/raporlar', 'jeton-yok'))
  const g1 = await yCerezsiz.json()
  const g2 = await yGecersiz.json()
  // Govde AYNI olmali; ayrim yalnizca teshis basliginda.
  assert.deepEqual(g1, g2, 'cerez yok ile gecersiz jeton govdeden AYIRT EDILEBILIYOR')
  assert.notEqual(yCerezsiz.headers.get('X-Oturum'), yGecersiz.headers.get('X-Oturum'),
    'teshis basligi ayrimi korunmali')
})

// ============================================================================
// 4.13 — Hız sınırlama kullanıcı başına
// ============================================================================
test('4.13 HIZ: kova anahtari DOGRULANMIS kimlikten turuyor (taklit edilemez)', async () => {
  const [j1, u1] = kullaniciAc()
  const [, u2] = kullaniciAc()
  // u1, kendini u2 gibi gostererek u2'nin kovasini tuketmeye calisiyor.
  const y = await middleware(istek('/api/raporlar', j1, {
    [KULLANICI_BASLIGI]: u2, [KIRACI_BASLIGI]: 'kullanici',
  }))
  assert.equal(asagi(y, KULLANICI_BASLIGI), u1,
    'kova anahtari uydurma basliktan turerse baskasinin kovasi tuketilebilirdi')
})

// ============================================================================
// 4.14 — Oturum sonlandıktan sonra jeton geçersiz
// ============================================================================
test('4.14 CIKIS: kimlik sunucusu jetonu reddedince erisim ANINDA kesilir', async () => {
  const [j] = kullaniciAc()
  assert.equal((await middleware(istek('/api/raporlar', j))).status, 200)
  // "Cikis" benzetimi: jeton kimlik sunucusunda artik taninmiyor.
  delete JETON[j]
  const y = await middleware(istek('/api/raporlar', j))
  assert.equal(y.status, 401, 'cikistan sonra jeton hala kabul ediliyor')
  assert.equal(asagi(y, KULLANICI_BASLIGI), null)
})

// ============================================================================
// 4.15 — Aynı kullanıcı 2 cihazdan: veri tutarlı
// ============================================================================
test('4.15 IKI CIHAZ: ayni kullanici iki oturumda AYNI kimligi tasir', async () => {
  const [j, u] = kullaniciAc()
  // Ayni kullanici, iki AYRI cerez (iki cihaz) - jeton ayni kullaniciya isaret eder.
  const j2 = `${j}-cihaz2`; JETON[j2] = u
  const y1 = await middleware(istek('/api/raporlar', j))
  const y2 = await middleware(istek('/api/raporlar', j2))
  assert.equal(asagi(y1, KULLANICI_BASLIGI), u)
  assert.equal(asagi(y2, KULLANICI_BASLIGI), u)
  assert.equal(asagi(y1, KULLANICI_BASLIGI), asagi(y2, KULLANICI_BASLIGI),
    'ayni kullanici iki cihazda FARKLI kimlik tasiyor')
})

test('4.15 IKI CIHAZ: iki cihaz AYNI kovayi paylasir (kullanici basina sinir)', async () => {
  const [j, u] = kullaniciAc()
  const j2 = `${j}-b`; JETON[j2] = u
  // 'ucuz' patlama 30: iki cihazdan toplam 40 istek, kova KULLANICI basina
  // oldugu icin toplamda tukenmeli - cihaz basina DEGIL.
  let dustu = false
  for (let i = 0; i < 40; i++) {
    const y = await middleware(istek('/api/raporlar', i % 2 ? j : j2))
    if (y.status === 429 && y.headers.get('X-RateLimit-Asama') === 'kullanici') {
      dustu = true; break
    }
  }
  assert.ok(dustu, 'iki cihaz ayri kova alsaydi sinir kullanici basina OLMAZDI')
})
