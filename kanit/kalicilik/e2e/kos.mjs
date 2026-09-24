// UÇTAN UCA KOŞUM — gösterge/çizim kalıcılığı, gerçek Chromium + gerçek localStorage.
//
// NEDEN VAR: frontend testleri çıplak node:test'tir, jsdom yoktur; GrafikTerminali
// render edilemez. Saf modüller orada sınanır; bileşenin kendisi (efekt sırası,
// yükleme/kaydetme kapıları, pagehide boşaltma) yalnızca burada görülebilir.
//
// ÇALIŞTIRMA (frontend bağımlılıkları kurulu olmalı; playwright-core projeye EKLENMEZ):
//   npm i --no-save --prefix <gecici-dizin> playwright-core@1.56.1
//   PLAYWRIGHT_CORE=<gecici-dizin>/node_modules/playwright-core/index.js \
//   CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
//   node kanit/kalicilik/e2e/kos.mjs [senaryo-adi-filtresi]
import { createServer } from 'node:http'
import { mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const burasi = dirname(fileURLToPath(import.meta.url))
const frontend = resolve(burasi, '../../../frontend')
const esbuild = createRequire(join(frontend, 'package.json'))('esbuild')
const pw = await import(process.env.PLAYWRIGHT_CORE ?? 'playwright-core')
const chromium = pw.chromium ?? pw.default.chromium

// ------------------------------------------------------------------ paketle + sun
const cikti = mkdtempSync(join(tmpdir(), 'kalicilik-e2e-'))
await esbuild.build({
  entryPoints: [join(burasi, 'giris.tsx')],
  bundle: true,
  outfile: join(cikti, 'paket.js'),
  jsx: 'automatic',
  nodePaths: [join(frontend, 'node_modules')],
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'error',
})
const html = '<!doctype html><meta charset="utf-8"><body style="background:#0f172a"><div id="kok" style="width:900px"></div><script src="/paket.js"></script>'
const sunucu = createServer((istek, yanit) => {
  if (istek.url.startsWith('/paket.js')) {
    yanit.writeHead(200, { 'content-type': 'text/javascript' })
    yanit.end(readFileSync(join(cikti, 'paket.js')))
    return
  }
  yanit.writeHead(200, { 'content-type': 'text/html' })
  yanit.end(html)
})
await new Promise((tamam) => sunucu.listen(0, '127.0.0.1', tamam))
const KOK = `http://127.0.0.1:${sunucu.address().port}`

const tarayici = await chromium.launch({ executablePath: process.env.CHROMIUM, headless: true })

// ------------------------------------------------------------------ yardımcılar
const GECIKME_PAYI_MS = 450 // debounce (300 ms) + render payı

async function ac(sayfa, { sembol = 'AAPL', kimlik = 'kullanici-A', prop = false } = {}) {
  const hatalar = []
  sayfa.on('pageerror', (hata) => hatalar.push(String(hata)))
  sayfa.hatalar = hatalar
  await sayfa.goto(`${KOK}/?sembol=${sembol}&kimlik=${kimlik}${prop ? '&prop=1' : ''}`)
  await sayfa.waitForSelector('section[aria-label="Grafik terminali"] canvas')
  await sayfa.waitForTimeout(150)
}
const gostergeDugmesi = (sayfa, etiket) => sayfa.locator(`button[aria-label="Göstergeler: ${etiket}"]`)
async function gostergeTikla(sayfa, etiket) {
  await gostergeDugmesi(sayfa, etiket).click()
}
async function basili(sayfa, etiket) {
  return (await gostergeDugmesi(sayfa, etiket).getAttribute('aria-pressed')) === 'true'
}
async function basiliListe(sayfa) {
  const sonuc = []
  for (const etiket of ['SMA 20', 'SMA 50', 'EMA 20', 'Bollinger (20, 2)', 'RSI 14', 'MACD (12, 26, 9)']) {
    if (await basili(sayfa, etiket)) sonuc.push(etiket)
  }
  return sonuc
}
async function yatayCiz(sayfa) {
  await sayfa.locator('button[aria-label="Çizim araçları: Yatay çizgi"]').click()
  const kutu = await sayfa.locator('section[aria-label="Grafik terminali"] canvas').first().boundingBox()
  await sayfa.mouse.click(kutu.x + kutu.width / 2, kutu.y + kutu.height / 2)
  await sayfa.locator('button[aria-label="Çizim araçları: İmleç"]').click()
}
async function cizimVar(sayfa) {
  return !(await sayfa.locator('button[aria-label="Tüm çizimleri silme"]').isDisabled())
}
/**
 * Her setItem çağrısını (anahtar, değer, süre) kaydeder. Son depo durumu tek
 * başına yetmez: bir sonraki render'da üzerine yazılan GEÇİCİ bir sızıntı
 * son durumda görünmez ama sekme o arada kapanırsa kalıcı olur.
 */
async function yazimKaydiKur(baglam) {
  await baglam.addInitScript(() => {
    const asil = Storage.prototype.setItem
    window.__yazimlar = []
    Storage.prototype.setItem = function (anahtar, deger) {
      const t0 = performance.now()
      try {
        return asil.call(this, anahtar, deger)
      } finally {
        window.__yazimlar.push({ anahtar, deger, ms: performance.now() - t0 })
      }
    }
  })
}
const yazimlar = (sayfa) => sayfa.evaluate(() => window.__yazimlar)
const depo = (sayfa) => sayfa.evaluate(() => Object.fromEntries(Object.entries(localStorage)))
const metin = (sayfa) => sayfa.locator('section[aria-label="Grafik terminali"]').innerText()
const bekle = (sayfa, ms = GECIKME_PAYI_MS) => sayfa.waitForTimeout(ms)
const CIZIM_A = 'alphawise:grafik:cizim:v1:kullanici-A:AAPL'
const CIZIM_B = 'alphawise:grafik:cizim:v1:kullanici-B:AAPL'
const GOSTERGE_A = 'alphawise:grafik:gosterge:v1:kullanici-A:AAPL'
const GOSTERGE_B = 'alphawise:grafik:gosterge:v1:kullanici-B:AAPL'

function esit(gercek, beklenen, mesaj) {
  const g = JSON.stringify(gercek)
  const b = JSON.stringify(beklenen)
  if (g !== b) throw new Error(`${mesaj}: beklenen ${b}, gelen ${g}`)
}

// ------------------------------------------------------------------ senaryolar
const senaryolar = []
const senaryo = (ad, govde) => senaryolar.push({ ad, govde })

senaryo('E1 yenileme: açılan göstergeler sayfa yenilenince geri gelir', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await gostergeTikla(s, 'SMA 20')
  await gostergeTikla(s, 'RSI 14')
  await bekle(s)
  await s.reload()
  await ac(s)
  esit(await basiliListe(s), ['SMA 20', 'RSI 14'], 'yenileme sonrası basılı göstergeler')
})

senaryo('E2 sembol değişimi: seçim sembole ait, geri dönünce geri gelir', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await gostergeTikla(s, 'SMA 20')
  await bekle(s)
  await s.evaluate(() => window.ciz('TSLA', undefined))
  await bekle(s)
  esit(await basiliListe(s), [], 'TSLA ilk açılış')
  await gostergeTikla(s, 'MACD (12, 26, 9)')
  await bekle(s)
  await s.evaluate(() => window.ciz('AAPL', undefined))
  await bekle(s)
  esit(await basiliListe(s), ['SMA 20'], 'AAPL geri dönüş')
  await s.evaluate(() => window.ciz('TSLA', undefined))
  await bekle(s)
  esit(await basiliListe(s), ['MACD (12, 26, 9)'], 'TSLA geri dönüş')
})

senaryo('E3 çizim yenileme: çizim sayfa yenilenince geri gelir', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await yatayCiz(s)
  await bekle(s)
  if (!(await cizimVar(s))) throw new Error('çizim oluşmadı (düzenek sorunu)')
  await s.reload()
  await ac(s)
  if (!(await cizimVar(s))) throw new Error('yenileme sonrası çizim yok')
  esit(JSON.parse((await depo(s))[CIZIM_A]).cizimler.length, 1, 'depodaki çizim sayısı')
})

senaryo('E4 (Y7) tek cihaz iki hesap: A-nın ayarları B-ye görünmez', async (baglam) => {
  const a = await baglam.newPage()
  await ac(a, { kimlik: 'kullanici-A' })
  await gostergeTikla(a, 'EMA 20')
  await yatayCiz(a)
  await bekle(a)
  await a.close()
  const b = await baglam.newPage()
  await ac(b, { kimlik: 'kullanici-B' })
  esit(await basiliListe(b), [], 'B göstergeleri')
  if (await cizimVar(b)) throw new Error('B, A-nın çizimini görüyor')
  const d = await depo(b)
  esit(JSON.parse(d[GOSTERGE_A]).gostergeler, ['ema20'], 'A kaydı yerinde')
})

senaryo('E5 (H-1) aynı sekmede kullanıcı değişimi: A-nın verisi B-nin anahtarına YAZILMAZ', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s, { kimlik: 'kullanici-A', prop: true })
  await gostergeTikla(s, 'Bollinger (20, 2)')
  await yatayCiz(s)
  await bekle(s)
  const aCizimleri = JSON.parse((await depo(s))[CIZIM_A]).cizimler.map((c) => c.id)
  if (aCizimleri.length !== 1) throw new Error('A çizimi oluşmadı (düzenek sorunu)')
  await s.evaluate(() => window.ciz('AAPL', 'kullanici-B'))
  await bekle(s)
  // Geçici sızıntı dahil: B anahtarına A-nın verisini taşıyan TEK bir yazım bile olmamalı.
  const sizanlar = (await yazimlar(s)).filter(
    (y) => (y.anahtar === CIZIM_B && aCizimleri.some((id) => y.deger.includes(id))) ||
      (y.anahtar === GOSTERGE_B && y.deger.includes('bollinger20')),
  )
  esit(sizanlar.map((y) => y.anahtar), [], 'B anahtarına A verisiyle yapılan yazımlar')
  const d = await depo(s)
  const bCizim = d[CIZIM_B] === undefined ? [] : JSON.parse(d[CIZIM_B]).cizimler
  const bGosterge = d[GOSTERGE_B] === undefined ? [] : JSON.parse(d[GOSTERGE_B]).gostergeler
  esit(bCizim.length, 0, 'B anahtarındaki çizim sayısı (sızıntı)')
  esit(bGosterge, [], 'B anahtarındaki göstergeler (sızıntı)')
  esit(await basiliListe(s), [], 'B ekranı')
})

senaryo('E6 (C4) bozuk ve ileri sürüm kayıt: çökme yok, görünür uyarı, sonra onarılır', async (baglam) => {
  const s = await baglam.newPage()
  await s.goto(`${KOK}/bos`)
  await s.evaluate(([g, c]) => {
    localStorage.setItem(g, '{bozuk json')
    localStorage.setItem(c, JSON.stringify({ v: 99, cizimler: [] }))
  }, [GOSTERGE_A, CIZIM_A])
  await ac(s)
  const t = await metin(s)
  if (!t.includes('Kayıtlı göstergeler: bozuk kayit sifirlandi')) throw new Error(`gösterge uyarısı yok: ${t}`)
  if (!t.includes('Kayıtlı çizimler: bilinmeyen surum (v=99) sifirlandi')) throw new Error(`çizim uyarısı yok: ${t}`)
  await gostergeTikla(s, 'SMA 50')
  await bekle(s)
  esit(JSON.parse((await depo(s))[GOSTERGE_A]).gostergeler, ['sma50'], 'bozuk kaydın üzerine geçerli kayıt')
})

senaryo('E7 (Y9) GERÇEK kota dolu: çökme yok, anlaşılır uyarı, seçim ekranda kalır', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  // Depoyu gerçek kotaya kadar doldur (tarayıcının kendi QuotaExceededError'u).
  const dolan = await s.evaluate(() => {
    const parca = 'x'.repeat(256 * 1024)
    let i = 0
    let ad = ''
    for (;;) {
      try { localStorage.setItem(`dolgu:${i}`, parca); i += 1 } catch (h) { ad = h.name; break }
    }
    for (let boyut = 128 * 1024; boyut >= 1; boyut = Math.floor(boyut / 2)) {
      try { localStorage.setItem(`dolgu:ince:${boyut}`, 'x'.repeat(boyut)) } catch { /* bir sonraki küçük boyut */ }
    }
    return { parca: i, ad }
  })
  if (dolan.ad !== 'QuotaExceededError') throw new Error(`tarayıcı hatası beklenmedik: ${dolan.ad}`)
  await gostergeTikla(s, 'RSI 14')
  await bekle(s)
  const uyari = await s.locator('[role="alert"]').innerText()
  if (!uyari.includes('Gösterge seçimi tarayıcı deposuna yazılamadı: tarayıcı deposu dolu')) throw new Error(`uyarı: ${uyari}`)
  if (!(await basili(s, 'RSI 14'))) throw new Error('seçim ekrandan düştü')
  // Yer açılınca bir sonraki kayıt başarılı olur ve uyarı kendiliğinden kalkar.
  await s.evaluate(() => { for (const a of Object.keys(localStorage)) if (a.startsWith('dolgu:')) localStorage.removeItem(a) })
  await gostergeTikla(s, 'SMA 20')
  await bekle(s)
  if ((await s.locator('[role="alert"]').count()) !== 0) throw new Error('yer açıldıktan sonra uyarı kalkmadı')
  esit(JSON.parse((await depo(s))[GOSTERGE_A]).gostergeler, ['sma20', 'rsi14'], 'yer açıldıktan sonra kayıt')
  console.log(`       (kota: ${dolan.parca} × 256 KiB parçada doldu)`)
})

senaryo('E8 localStorage kapalı (gizli mod benzetimi): terminal çalışır, not görünür', async (baglam) => {
  await baglam.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get() { throw new DOMException('depolama erişimi engellendi', 'SecurityError') },
    })
  })
  const s = await baglam.newPage()
  await ac(s)
  const t = await metin(s)
  if (!t.includes('Çizimler tarayıcı deposuna yazılamadı: depolama erişimi engellendi')) throw new Error(`not yok: ${t}`)
  await gostergeTikla(s, 'MACD (12, 26, 9)')
  await yatayCiz(s)
  await bekle(s)
  if (!(await basili(s, 'MACD (12, 26, 9)'))) throw new Error('gösterge açılamadı')
  if (!(await cizimVar(s))) throw new Error('çizim yapılamadı')
})

/** Geçerli bir `Cizim` (cizim-model şeması) - büyük kayıt senaryoları için. */
function ornekCizim(i) {
  return {
    v: 1, id: `yuk-${i}`, tip: 'trend',
    noktalar: [{ t_utc: Date.UTC(2025, 1, 3) + i * 86_400_000, fiyat: 100 + i / 10 }, { t_utc: Date.UTC(2025, 2, 3) + i * 86_400_000, fiyat: 101 + i / 10 }],
    stil: { renk: '#D4AF37', kalinlik: 2 }, olusturma_utc: 1758700000000 + i,
  }
}

senaryo('E9 (Y10) hızlı art arda 20 gösterge değişimi (yarış): en fazla 2 yazım, son durum doğru', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await bekle(s)
  const once = (await yazimlar(s)).length
  for (let i = 0; i < 10; i += 1) {
    await gostergeTikla(s, 'SMA 20')
    await gostergeTikla(s, 'EMA 20')
  }
  await gostergeTikla(s, 'EMA 20') // net sonuç: yalnızca EMA 20 açık
  await bekle(s)
  const gostergeYazimlari = (await yazimlar(s)).slice(once).filter((y) => y.anahtar === GOSTERGE_A)
  console.log(`       (21 tıklama → ${gostergeYazimlari.length} gösterge yazımı)`)
  if (gostergeYazimlari.length > 2) throw new Error(`${gostergeYazimlari.length} yazım (debounce yok)`)
  esit(JSON.parse((await depo(s))[GOSTERGE_A]).gostergeler, ['ema20'], 'son durum')
  await s.reload()
  await ac(s)
  esit(await basiliListe(s), ['EMA 20'], 'yenileme sonrası')
})

senaryo('E10 (C5) debounce penceresi içinde yenileme/kapama: son değişiklik KAYBOLMAZ', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await bekle(s)
  await gostergeTikla(s, 'Bollinger (20, 2)')
  await s.reload() // BEKLEMEDEN: yazım 300 ms penceresinin içinde
  await ac(s)
  esit(await basiliListe(s), ['Bollinger (20, 2)'], 'pencere içi yenileme')
  await gostergeTikla(s, 'RSI 14')
  await s.close({ runBeforeUnload: true }) // sekme kapanışı
  const s2 = await baglam.newPage()
  await ac(s2)
  esit(await basiliListe(s2), ['Bollinger (20, 2)', 'RSI 14'], 'pencere içi sekme kapanışı')
})

senaryo('E11 (Y14) 1000 kayıtlı çizim: yükleme + ekleme çalışır, sayfa hatası yok', async (baglam) => {
  const s = await baglam.newPage()
  await s.goto(`${KOK}/bos`)
  await s.evaluate(([c, liste]) => localStorage.setItem(c, JSON.stringify({ v: 1, cizimler: liste })),
    [CIZIM_A, Array.from({ length: 1000 }, (_, i) => ornekCizim(i))])
  await ac(s)
  await yatayCiz(s)
  await bekle(s)
  const kayit = (await depo(s))[CIZIM_A]
  esit(JSON.parse(kayit).cizimler.length, 1001, 'çizim sayısı')
  console.log(`       (1001 çizim = ${kayit.length} karakter)`)
})

senaryo('P1 (Y10) yazım maliyeti ölçümü: JSON.stringify + setItem, gerçek Chromium', async (baglam) => {
  const s = await baglam.newPage()
  await s.goto(`${KOK}/bos`)
  const olcumler = await s.evaluate((liste) => {
    const sonuc = []
    const olc = (ad, veri) => {
      const sureler = []
      for (let i = 0; i < 200; i += 1) {
        const t0 = performance.now()
        localStorage.setItem('olcum', JSON.stringify(veri))
        sureler.push(performance.now() - t0)
      }
      sureler.sort((x, y) => x - y)
      sonuc.push({ ad, karakter: JSON.stringify(veri).length, p50: sureler[100], p95: sureler[189], azami: sureler[199] })
    }
    olc('gösterge (6 açık)', { v: 1, gostergeler: ['sma20', 'sma50', 'ema20', 'bollinger20', 'rsi14', 'macd'], guncelleme_utc: 1 })
    for (const n of [10, 100, 1000, 5000]) olc(`${n} çizim`, { v: 1, cizimler: liste.slice(0, n) })
    localStorage.removeItem('olcum')
    return sonuc
  }, Array.from({ length: 5000 }, (_, i) => ornekCizim(i)))
  for (const o of olcumler) {
    console.log(`       ${o.ad.padEnd(18)} ${String(o.karakter).padStart(8)} kr  p50 ${o.p50.toFixed(3)} ms  p95 ${o.p95.toFixed(3)} ms  azami ${o.azami.toFixed(3)} ms`)
  }
  const bin = olcumler.find((o) => o.ad === '1000 çizim')
  if (bin.p95 > 50) throw new Error(`1000 çizimde p95 ${bin.p95} ms > 50 ms`)
})

// ------------------------------------------------------------------ koş
const filtre = process.argv[2]
let kalan = 0
for (const { ad, govde } of senaryolar) {
  if (filtre && !ad.includes(filtre)) continue
  const baglam = await tarayici.newContext()
  await yazimKaydiKur(baglam)
  try {
    await govde(baglam)
    const hatalar = baglam.pages().flatMap((s) => s.hatalar ?? [])
    if (hatalar.length > 0) throw new Error(`sayfa hatası: ${hatalar.join(' | ')}`)
    console.log(`GEÇTİ  ${ad}`)
  } catch (hata) {
    kalan += 1
    console.log(`KALDI  ${ad}\n       ${hata.message.split('\n')[0]}`)
  } finally {
    await baglam.close()
  }
}
await tarayici.close()
sunucu.close()
console.log(`\n${senaryolar.filter((s) => !filtre || s.ad.includes(filtre)).length - kalan} geçti, ${kalan} kaldı`)
process.exit(kalan === 0 ? 0 : 1)
