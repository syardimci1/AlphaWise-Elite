// UÇTAN UCA KOŞUM — karşılaştırma modu, gerçek Chromium + gerçek localStorage.
//
// NEDEN VAR: frontend testleri çıplak node:test'tir, jsdom yoktur; GrafikTerminali
// render edilemez. Saf karar mantığı (karsilastirma.ts) orada sınanır; bileşenin
// kendisi (efekt sırası, gizle/göster, klavye, piksel boşluğu, kalıcılık kapıları,
// süre) yalnızca burada görülebilir.
//
// ÇALIŞTIRMA (frontend bağımlılıkları kurulu olmalı; playwright-core projeye EKLENMEZ):
//   npm i --no-save --prefix <gecici-dizin> playwright-core@1.56.1
//   PLAYWRIGHT_CORE=<gecici-dizin>/node_modules/playwright-core/index.js \
//   CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
//   node kanit/karsilastirma/e2e/kos.mjs [senaryo-adi-filtresi]
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
const cikti = mkdtempSync(join(tmpdir(), 'karsilastirma-e2e-'))
await esbuild.build({
  entryPoints: [join(burasi, 'giris.tsx')],
  bundle: true,
  outfile: join(cikti, 'paket.js'),
  jsx: 'automatic',
  nodePaths: [join(frontend, 'node_modules')],
  alias: { '@': join(frontend, 'src') },
  define: { 'process.env.NODE_ENV': process.env.TANI ? '"development"' : '"production"' },
  conditions: process.env.TANI ? ['development'] : [],
  minify: false,
  logLevel: 'error',
})
const sunucu = createServer((istek, yanit) => {
  if (istek.url.startsWith('/paket.js')) {
    yanit.writeHead(200, { 'content-type': 'text/javascript' })
    yanit.end(readFileSync(join(cikti, 'paket.js')))
    return
  }
  const dar = new URL(istek.url, 'http://x').searchParams.get('dar') === '1'
  yanit.writeHead(200, { 'content-type': 'text/html' })
  yanit.end(
    `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">` +
      `<body style="margin:0;background:#0f172a"><div id="kok" style="${dar ? 'padding:0 16px' : 'width:900px'}"></div>` +
      `<script src="/paket.js"></script>`,
  )
})
await new Promise((tamam) => sunucu.listen(0, '127.0.0.1', tamam))
const KOK = `http://127.0.0.1:${sunucu.address().port}`
const tarayici = await chromium.launch({ executablePath: process.env.CHROMIUM, headless: true })

// ------------------------------------------------------------------ yardımcılar
const GECIKME_PAYI_MS = 450 // debounce (300 ms) + render payı
const BOLUM = 'section[aria-label="Grafik terminali"]'
const LEJANT = 'ul[aria-label="Karşılaştırma lejantı"]'
const MOD_KARS = 'div[role="group"][aria-label="Görünüm"] button:has-text("Karşılaştırma")'
const MOD_TEK = 'div[role="group"][aria-label="Görünüm"] button:has-text("Tek sembol")'
const GIRDI = '#karsilastirma-sembol'
const EKLE = 'button[aria-label="Sembolü karşılaştırmaya ekleme"]'
const DURUM = `${BOLUM} [role="status"]`
const NOT = `${BOLUM} [data-karsilastirma-notu]`
const MUM = `${BOLUM} [data-mum-grafigi]`
const KARS_GRAFIK = `${BOLUM} [data-karsilastirma-grafigi]`
const ANAHTAR = (kimlik, sembol) => `alphawise:grafik:karsilastirma:v1:${kimlik}:${sembol}`

async function ac(sayfa, { sembol = 'AAPL', kimlik = 'kullanici-A', dar = false } = {}) {
  const hatalar = []
  sayfa.on('pageerror', (hata) => hatalar.push(process.env.TANI ? String(hata.stack) : String(hata)))
  sayfa.hatalar = hatalar
  await sayfa.goto(`${KOK}/?sembol=${sembol}&kimlik=${kimlik}${dar ? '&dar=1' : ''}`)
  await sayfa.waitForSelector(`${BOLUM} canvas`, { state: 'attached' })
  await sayfa.waitForTimeout(200)
}
const bekle = (sayfa, ms = GECIKME_PAYI_MS) => sayfa.waitForTimeout(ms)
const depo = (sayfa) => sayfa.evaluate(() => Object.fromEntries(Object.entries(localStorage)))
const gorunur = (sayfa, secici) => sayfa.locator(secici).first().isVisible()
async function ekleKlavyeyle(sayfa, sembol) {
  // Reddedilen girdi kutuda KALIR (kullanıcı düzeltebilsin); yeni deneme önce kutuyu seçip üzerine yazar.
  await sayfa.locator(GIRDI).focus()
  await sayfa.keyboard.press('Control+A')
  await sayfa.keyboard.type(sembol)
  await sayfa.keyboard.press('Enter')
  await sayfa.waitForTimeout(150)
}
async function lejant(sayfa) {
  if ((await sayfa.locator(LEJANT).count()) === 0) return []
  return sayfa.locator(`${LEJANT} > li`).evaluateAll((lar) =>
    lar.map((li) => ({
      sembol: li.querySelector('strong')?.textContent ?? '',
      deger: li.querySelector('[data-lejant-deger]')?.textContent ?? '',
      renk: getComputedStyle(li.querySelector('span[aria-hidden]')).backgroundColor,
      not: li.querySelector('[data-lejant-not]')?.textContent ?? '',
      metin: li.innerText,
    })),
  )
}
async function karsilastirmaHazir(sayfa, satir) {
  await sayfa.waitForFunction(
    ([secici, n]) => document.querySelectorAll(`${secici} > li`).length === n,
    [LEJANT, satir],
    { timeout: 5000 },
  )
  await sayfa.waitForTimeout(150)
}
function esit(gercek, beklenen, mesaj) {
  const g = JSON.stringify(gercek)
  const b = JSON.stringify(beklenen)
  if (g !== b) throw new Error(`${mesaj}: beklenen ${b}, gelen ${g}`)
}
function dogru(kosul, mesaj) {
  if (!kosul) throw new Error(mesaj)
}
/**
 * Karşılaştırma grafiğinde imleci soldan sağa gezdirip lejant tarihinin `hedef`
 * olduğu x'i bulur (kütüphane API'si dışarıdan erişilemez; lejant tek gerçek kaynak).
 */
async function imleciTariheGetir(sayfa, hedef) {
  const kutu = await sayfa.locator(`${KARS_GRAFIK} canvas`).first().boundingBox()
  const y = kutu.y + kutu.height / 2
  for (let x = kutu.x + 2; x < kutu.x + kutu.width - 60; x += 1) {
    await sayfa.mouse.move(x, y)
    const tarih = await sayfa.locator(`${LEJANT} > li`).first().evaluate((li) => li.innerText)
    if (tarih.includes(hedef)) return x
  }
  throw new Error(`imleç ${hedef} tarihine getirilemedi`)
}

// ------------------------------------------------------------------ senaryolar
const senaryolar = []
const senaryo = (ad, govde) => senaryolar.push({ ad, govde })

senaryo('K1 (S1, Y11) YALNIZ KLAVYEYLE: moda geç, sembol ekle → 2 çizgi + lejant, mum gizli', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  // Tab ile Görünüm düğmesine ulaş (fare yok).
  let bulundu = false
  for (let i = 0; i < 40 && !bulundu; i += 1) {
    await s.keyboard.press('Tab')
    bulundu = await s.evaluate(() => document.activeElement?.textContent === 'Karşılaştırma')
  }
  dogru(bulundu, 'Karşılaştırma düğmesi Tab ile odaklanamadı')
  await s.keyboard.press('Enter')
  await s.waitForTimeout(150)
  esit(await s.locator(MOD_KARS).getAttribute('aria-pressed'), 'true', 'aria-pressed')
  // Sembol girdisine Tab ile ilerle.
  bulundu = false
  for (let i = 0; i < 10 && !bulundu; i += 1) {
    await s.keyboard.press('Tab')
    bulundu = await s.evaluate(() => document.activeElement?.id === 'karsilastirma-sembol')
  }
  dogru(bulundu, 'sembol girdisi Tab ile odaklanamadı')
  await s.keyboard.type('msft')
  await s.keyboard.press('Enter')
  await karsilastirmaHazir(s, 2)
  const l = await lejant(s)
  esit(l.map((x) => x.sembol), ['AAPL', 'MSFT'], 'lejant sembolleri')
  esit(await gorunur(s, MUM), false, 'mum grafiği gizli olmalı')
  esit(await gorunur(s, KARS_GRAFIK), true, 'karşılaştırma grafiği görünür olmalı')
  dogru((await s.locator(DURUM).innerText()).includes('MSFT'), 'ekleme duyurulmadı')
  // Çıkarma da klavyeyle: düğme odaklanır, Enter; odak girdiye döner.
  await s.locator('button[aria-label="Karşılaştırmadan çıkar: MSFT"]').focus()
  await s.keyboard.press('Enter')
  await s.waitForTimeout(150)
  esit(await s.evaluate(() => document.activeElement?.id), 'karsilastirma-sembol', 'çıkarma sonrası odak')
})

senaryo('K2 (C1) taban gününde TÜM seriler %0,00; taban notu tarihi yazar', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await ekleKlavyeyle(s, 'NVDA')
  await karsilastirmaHazir(s, 3)
  const not = await s.locator(`${BOLUM}`).innerText()
  // NVDA 2025-03-03'te başlıyor: ortak taban o gün.
  dogru(not.includes('Başlangıç (%0): 2025-03-03'), 'taban notu 2025-03-03 değil')
  await imleciTariheGetir(s, '2025-03-03')
  const l = await lejant(s)
  esit(l.map((x) => x.deger), ['%0,00', '%0,00', '%0,00'], 'taban günü değerleri')
  dogru(l[0].not.includes('ortak başlangıç öncesinde'), `AAPL taban öncesi notu yok: ${l[0].not}`)
})

senaryo('K3 (C2, FAZ4) 4. sembol: düğme devre dışı + neden görünür, Enter eklemez, istek atılmaz', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await ekleKlavyeyle(s, 'NVDA')
  await karsilastirmaHazir(s, 3)
  esit(await s.locator(EKLE).isDisabled(), true, 'ekle düğmesi devre dışı olmalı')
  dogru((await s.locator('#karsilastirma-dolu').innerText()).includes('En fazla 3'), 'neden metni yok')
  esit(await s.locator(GIRDI).getAttribute('aria-describedby'), 'karsilastirma-dolu', 'girdi nedeni anons etmeli')
  await ekleKlavyeyle(s, 'TSLA')
  await s.waitForTimeout(300)
  esit((await lejant(s)).map((x) => x.sembol), ['AAPL', 'MSFT', 'NVDA'], '4. sembol eklenmemeli, en eski çıkmamalı')
  esit((await s.evaluate(() => window.istekler)).includes('TSLA'), false, 'TSLA için istek atılmamalı')
})

senaryo('K4 (FAZ4) aynı sembol iki kez ve ana sembolün kendisi: reddedilir, neden duyurulur', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await ekleKlavyeyle(s, ' msft ')
  dogru((await s.locator(DURUM).innerText()).includes('zaten var'), 'yinelenen nedeni yok')
  await ekleKlavyeyle(s, 'aapl')
  dogru((await s.locator(DURUM).innerText()).includes('ana sembol'), 'ana sembol nedeni yok')
  await ekleKlavyeyle(s, 'A..B')
  dogru((await s.locator(DURUM).innerText()).includes('geçersiz'), 'geçersiz biçim nedeni yok')
  await karsilastirmaHazir(s, 2)
  esit((await s.evaluate(() => window.istekler)).filter((x) => x === 'MSFT').length, 1, 'MSFT bir kez çekilmeli')
})

senaryo('K5 (C4, Y9) eksik günler: lejant sayar, imleç "veri yok" der, çizgi boşluğu KÖPRÜLEMEZ (piksel)', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await karsilastirmaHazir(s, 2)
  const l = await lejant(s)
  dogru(l[1].not.startsWith('5 gün veri yok'), `MSFT notu: ${l[1].not}`)
  // Fikstür: 100–104. işlem günleri (0 tabanlı) eksik. Orta gün = 102.
  const tarihler = await s.evaluate(() => {
    const gunler = []
    for (let i = 0; gunler.length < 105; i += 1) {
      const g = new Date(Date.UTC(2025, 0, 2) + i * 86_400_000)
      if (g.getUTCDay() !== 0 && g.getUTCDay() !== 6) gunler.push(g.toISOString().slice(0, 10))
    }
    return { orta: gunler[102], ilk: gunler[100] }
  })
  dogru(l[1].not.includes(tarihler.ilk), 'eksik günün tarihi notta yok')
  const x = await imleciTariheGetir(s, tarihler.orta)
  const imlecte = await lejant(s)
  esit(imlecte[1].deger, 'veri yok', 'eksik günde MSFT değeri')
  dogru(imlecte[0].deger !== 'veri yok', 'AAPL o gün dolu olmalı')
  // Piksel: imleci kaldır, eksik günün sütununda MSFT turuncusu (#d95926) olmamalı;
  // pozitif kontrol: 30 px soldaki sütunda (veri var) turuncu olmalı.
  await s.mouse.move(0, 0)
  await s.waitForTimeout(150)
  const kutu = await s.locator(`${KARS_GRAFIK} canvas`).first().boundingBox()
  const png = await s.screenshot({ clip: { x: kutu.x, y: kutu.y, width: kutu.width, height: kutu.height } })
  const sayim = await s.evaluate(
    async ({ b64, sutunlar }) => {
      const resim = new Image()
      resim.src = `data:image/png;base64,${b64}`
      await resim.decode()
      const kanvas = document.createElement('canvas')
      kanvas.width = resim.width
      kanvas.height = resim.height
      const ctx = kanvas.getContext('2d')
      ctx.drawImage(resim, 0, 0)
      return sutunlar.map((sx) => {
        const veri = ctx.getImageData(Math.round(sx), 0, 1, kanvas.height).data
        let n = 0
        for (let i = 0; i < veri.length; i += 4) {
          if (Math.abs(veri[i] - 0xd9) < 30 && Math.abs(veri[i + 1] - 0x59) < 30 && Math.abs(veri[i + 2] - 0x26) < 30) n += 1
        }
        return n
      })
    },
    { b64: png.toString('base64'), sutunlar: [x - kutu.x, x - kutu.x - 30] },
  )
  console.log(`       turuncu piksel: eksik gün sütunu ${sayim[0]}, 30 px sol (veri var) ${sayim[1]}`)
  esit(sayim[0], 0, 'eksik gün sütununda köprü çizgisi')
  dogru(sayim[1] > 0, 'pozitif kontrol başarısız: veri olan sütunda turuncu yok')
})

senaryo('K6 (C6) mod gidiş-dönüşü: mum grafiği (yakınlaştırma, çizim, gösterge) PİKSELİ PİKSELİNE aynı', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator('button[aria-label="Göstergeler: SMA 20"]').click()
  await s.locator('button[aria-label="Çizim araçları: Yatay çizgi"]').click()
  const kutu = await s.locator(`${MUM} canvas`).first().boundingBox()
  await s.mouse.click(kutu.x + kutu.width / 2, kutu.y + kutu.height / 2)
  await s.locator('button[aria-label="Çizim araçları: İmleç"]').click()
  // Yakınlaştır (tekerlek) — kullanıcının kurduğu görünüm.
  await s.mouse.move(kutu.x + kutu.width / 2, kutu.y + kutu.height / 2)
  await s.mouse.wheel(0, -600)
  await s.waitForTimeout(300)
  await s.mouse.move(0, 0)
  await s.waitForTimeout(150)
  const once = await s.locator(MUM).screenshot()
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await karsilastirmaHazir(s, 2)
  await s.setViewportSize({ width: 1000, height: 800 }) // gizliyken yeniden boyutlandırma
  await s.setViewportSize({ width: 1280, height: 720 })
  await s.locator(MOD_TEK).click()
  await s.waitForTimeout(300)
  const sonra = await s.locator(MUM).screenshot()
  esit(Buffer.compare(once, sonra), 0, 'mum grafiği geçiş sonrası farklı (görünüm/çizim/gösterge kaybı)')
  esit(await s.locator('button[aria-label="Göstergeler: SMA 20"]').getAttribute('aria-pressed'), 'true', 'SMA 20')
  esit(await s.locator('button[aria-label="Tüm çizimleri silme"]').isDisabled(), false, 'çizim duruyor olmalı')
  // Liste tek modda korunur; geri dönünce aynı semboller, istek TEKRARLANMAZ.
  await s.locator(MOD_KARS).click()
  await karsilastirmaHazir(s, 2)
  esit((await s.evaluate(() => window.istekler)).filter((x) => x === 'MSFT').length, 1, 'MSFT yeniden çekilmemeli')
})

senaryo('K7 (C5) kalıcılık: yenileme sonrası mod + semboller + renkler geri gelir; B hesabı görmez', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await ekleKlavyeyle(s, 'NVDA')
  await karsilastirmaHazir(s, 3)
  await s.locator('button[aria-label="Karşılaştırmadan çıkar: MSFT"]').click()
  await karsilastirmaHazir(s, 2)
  const renkOnce = (await lejant(s)).map((x) => [x.sembol, x.renk])
  await bekle(s)
  const kayit = JSON.parse((await depo(s))[ANAHTAR('kullanici-A', 'AAPL')])
  esit([kayit.v, kayit.mod, kayit.semboller], [1, 'karsilastirma', [{ sembol: 'NVDA', yuva: 2 }]], 'depodaki kayıt')
  await s.reload()
  await ac(s)
  await karsilastirmaHazir(s, 2)
  esit((await lejant(s)).map((x) => [x.sembol, x.renk]), renkOnce, 'yenileme sonrası semboller/renkler')
  esit(renkOnce[1][1], 'rgb(25, 158, 112)', 'NVDA yuva 2 rengini korumalı (MSFT çıkınca turuncuya kaymamalı)')
  const b = await baglam.newPage()
  await ac(b, { kimlik: 'kullanici-B' })
  esit(await b.locator(MOD_TEK).getAttribute('aria-pressed'), 'true', 'B hesabı tek modda açılmalı')
  esit((await depo(b))[ANAHTAR('kullanici-B', 'AAPL')], undefined, 'B için kayıt yazılmamalı (yankı yok)')
})

senaryo('K8 (S6, FAZ4) tek sembol ve veri gelmeyen sembol → mum grafiğine düşer, neden görünür, yeniden dener', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await s.waitForTimeout(150)
  esit(await gorunur(s, MUM), true, 'ek sembol yokken mum görünür olmalı')
  dogru((await s.locator(NOT).innerText()).includes('en az bir sembol daha'), 'tek seri nedeni yok')
  await ekleKlavyeyle(s, 'HATA')
  await s.waitForSelector(`${NOT}:has-text("HTTP 500")`)
  esit(await gorunur(s, MUM), true, 'hatalı sembolde mum görünür olmalı')
  dogru((await s.locator(NOT).innerText()).includes('tek seri gösteriliyor'), 'yetersiz nedeni yok')
  await s.locator('button[aria-label="Karşılaştırmadan çıkar: HATA"]').click()
  await ekleKlavyeyle(s, 'HATA')
  await s.waitForSelector(`${NOT}:has-text("HTTP 500")`)
  esit((await s.evaluate(() => window.istekler)).filter((x) => x === 'HATA').length, 2, 'çıkar+ekle yeniden denemeli')
  await s.locator('button[aria-label="Karşılaştırmadan çıkar: HATA"]').click()
  await ekleKlavyeyle(s, 'BOS')
  await s.waitForSelector(`${NOT}:has-text("BOS")`)
  esit(await gorunur(s, MUM), true, 'boş veride mum görünür olmalı')
  // Çalışan bir ek sembol + hatalı bir ek: karşılaştırma çizilir, hata ayrıca görünür.
  await s.locator('button[aria-label="Karşılaştırmadan çıkar: BOS"]').click()
  await ekleKlavyeyle(s, 'MSFT')
  await ekleKlavyeyle(s, 'HATA')
  await karsilastirmaHazir(s, 2)
  dogru((await s.locator(NOT).innerText()).includes('HATA: fiyat verisi okunamadı'), 'hata notu yok')
})

senaryo('K9 (C1) tarih aralıkları kesişmiyor → sahte taban yok, neden görünür', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'UZAK')
  await s.waitForSelector(`${NOT}:has-text("kesişmiyor")`)
  esit(await s.locator(LEJANT).count(), 0, 'lejant/çizgi olmamalı')
})

senaryo('K10 (C6) karşılaştırma modunda Delete/Backspace görünmeyen çizimi SİLMEZ', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator('button[aria-label="Çizim araçları: Yatay çizgi"]').click()
  const kutu = await s.locator(`${MUM} canvas`).first().boundingBox()
  await s.mouse.click(kutu.x + kutu.width / 2, kutu.y + kutu.height / 2)
  await s.locator('button[aria-label="Çizim araçları: İmleç"]').click()
  await s.mouse.click(kutu.x + kutu.width / 2, kutu.y + kutu.height / 2) // seç
  await s.locator(MOD_KARS).click()
  await s.locator(MOD_KARS).focus()
  await s.keyboard.press('Delete')
  await s.keyboard.press('Backspace')
  await s.locator(MOD_TEK).click()
  esit(await s.locator('button[aria-label="Tüm çizimleri silme"]').isDisabled(), false, 'çizim silinmiş')
})

senaryo('K11 (Y11) 390 px: yatay kaydırma yok, tüm denetimler ekranda, 3 sembol', async (baglam) => {
  // DİKKAT: BrowserContext.newPage() viewport seçeneği ALMAZ (ilk koşuda sayfa sessizce 1280 px açıldı).
  const s = await baglam.newPage()
  await s.setViewportSize({ width: 390, height: 844 })
  await ac(s, { dar: true })
  esit(await s.evaluate(() => window.innerWidth), 390, 'görüntü alanı 390 px olmalı')
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await ekleKlavyeyle(s, 'NVDA')
  await karsilastirmaHazir(s, 3)
  const olcu = await s.evaluate(() => ({ kaydirma: document.documentElement.scrollWidth, pencere: window.innerWidth }))
  dogru(olcu.kaydirma <= olcu.pencere, `yatay taşma: ${olcu.kaydirma} > ${olcu.pencere}`)
  for (const secici of [MOD_KARS, MOD_TEK, GIRDI, EKLE, 'button[aria-label="Karşılaştırmadan çıkar: NVDA"]', LEJANT, KARS_GRAFIK]) {
    const k = await s.locator(secici).first().boundingBox()
    dogru(k !== null && k.x >= 0 && k.x + k.width <= 390 + 0.5, `${secici} ekran dışında: ${JSON.stringify(k)}`)
  }
  const cikar = await s.locator('button[aria-label="Karşılaştırmadan çıkar: NVDA"]').boundingBox()
  console.log(`       çıkar düğmesi ${cikar.width.toFixed(0)}×${cikar.height.toFixed(0)} px, sayfa genişliği ${olcu.kaydirma}`)
  dogru(cikar.width >= 24 && cikar.height >= 24, 'çıkar düğmesi 24×24 px dokunma hedefinin altında')
  await s.screenshot({ path: join(burasi, '../k11_390px.png'), fullPage: true })
})

senaryo('K12 (C1, FAZ4) 1000 kat farklı fiyat ölçeği: normalize sonrası AYNI yüzdeler', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'PAHALI')
  await karsilastirmaHazir(s, 2)
  const kutu = await s.locator(`${KARS_GRAFIK} canvas`).first().boundingBox()
  const farklar = []
  for (const oran of [0.2, 0.5, 0.8]) {
    await s.mouse.move(kutu.x + kutu.width * oran * 0.85, kutu.y + kutu.height / 2)
    const l = await lejant(s)
    farklar.push([l[0].deger, l[1].deger])
    esit(l[0].deger, l[1].deger, 'AAPL ve PAHALI (×1000) aynı yüzdeyi göstermeli')
  }
  console.log(`       örnek (AAPL, PAHALI): ${farklar.map((f) => f.join(' = ')).join(' · ')}`)
})

senaryo('K13 (C5) "Kayıtlı ayarları sıfırla" karşılaştırma kaydını da siler, geri yazılmaz', async (baglam) => {
  const s = await baglam.newPage()
  await ac(s)
  await s.locator(MOD_KARS).click()
  await ekleKlavyeyle(s, 'MSFT')
  await karsilastirmaHazir(s, 2)
  await bekle(s)
  dogru((await depo(s))[ANAHTAR('kullanici-A', 'AAPL')] !== undefined, 'kayıt yazılmamış')
  await s.locator(MOD_TEK).click()
  s.once('dialog', (d) => d.accept())
  await s.locator('button[aria-label="Bu sembol için kayıtlı gösterge, çizim ve karşılaştırma ayarlarını silme"]').click()
  await bekle(s)
  esit((await depo(s))[ANAHTAR('kullanici-A', 'AAPL')], undefined, 'karşılaştırma kaydı silinmedi ya da geri yazıldı')
  await s.locator(MOD_KARS).click()
  esit(await s.locator(`${BOLUM} ul[aria-label="Karşılaştırılan semboller"] > li`).count(), 1, 'yalnızca ana sembol kalmalı')
})

senaryo('K14 başka sekme karşılaştırma kaydını değiştirince görünür uyarı', async (baglam) => {
  const a = await baglam.newPage()
  await ac(a)
  const b = await baglam.newPage()
  await ac(b)
  await b.locator(MOD_KARS).click()
  await ekleKlavyeyle(b, 'MSFT')
  await bekle(b)
  await a.waitForTimeout(200)
  dogru((await a.locator(BOLUM).innerText()).includes('başka bir sekmede değişti'), 'A sekmesinde uyarı yok')
})

senaryo('K15 (Y10) 3 sembol × 2 yıl ve 3 × 1500 bar: çizim ≤ 1 sn (gerçek Chromium ölçümü)', async (baglam) => {
  for (const [ana, ekler, etiket] of [
    ['PA', ['PBB', 'PCCC'], '3 × 2 yıl'],
    ['QA', ['QBB', 'QCCC'], '3 × 1500 bar'],
  ]) {
    const olcumler = []
    for (let tekrar = 0; tekrar < 5; tekrar += 1) {
      const s = await baglam.newPage()
      await ac(s, { sembol: ana, kimlik: `perf-${tekrar}` })
      await s.locator(MOD_KARS).click()
      await ekleKlavyeyle(s, ekler[0])
      await ekleKlavyeyle(s, ekler[1])
      await karsilastirmaHazir(s, 3)
      // Veri önbellekte: tek → karşılaştırma geçişinin tamamını ölç (tıklama → lejant + boyanmış kare).
      await s.locator(MOD_TEK).click()
      await s.waitForTimeout(100)
      const sure = await s.evaluate(async (lejantSecici) => {
        const dugme = [...document.querySelectorAll('div[role="group"][aria-label="Görünüm"] button')].find(
          (d) => d.textContent === 'Karşılaştırma',
        )
        performance.clearMeasures('karsilastirma-cizim')
        const t0 = performance.now()
        dugme.click()
        await new Promise((tamam) => {
          const kontrol = () =>
            document.querySelectorAll(`${lejantSecici} > li`).length === 3 &&
            performance.getEntriesByName('karsilastirma-cizim').length > 0
              ? tamam()
              : requestAnimationFrame(kontrol)
          kontrol()
        })
        await new Promise((tamam) => requestAnimationFrame(() => tamam()))
        return {
          toplam: performance.now() - t0,
          cizim: performance.getEntriesByName('karsilastirma-cizim').at(-1).duration,
        }
      }, LEJANT)
      const bar = await s.evaluate(() => window.istekler.length)
      olcumler.push({ ...sure, istek: bar })
      await s.close()
    }
    const toplamlar = olcumler.map((o) => o.toplam).sort((x, y) => x - y)
    const cizimler = olcumler.map((o) => o.cizim).sort((x, y) => x - y)
    console.log(
      `       ${etiket}: tık→boyanmış kare medyan ${toplamlar[2].toFixed(1)} ms, azami ${toplamlar[4].toFixed(1)} ms · ` +
        `setData→kare medyan ${cizimler[2].toFixed(1)} ms, azami ${cizimler[4].toFixed(1)} ms (5 tekrar)`,
    )
    dogru(toplamlar[4] <= 1000, `${etiket}: ${toplamlar[4]} ms > 1000 ms`)
  }
})

// ------------------------------------------------------------------ koş
const filtre = process.argv[2]
let kalan = 0
for (const { ad, govde } of senaryolar) {
  if (filtre && !ad.includes(filtre)) continue
  const baglam = await tarayici.newContext({ viewport: { width: 1280, height: 720 } })
  try {
    await govde(baglam)
    const hatalar = baglam.pages().flatMap((s) => s.hatalar ?? [])
    if (hatalar.length > 0) throw new Error(`sayfa hatası: ${hatalar.join(' | ')}`)
    console.log(`GEÇTİ  ${ad}`)
  } catch (hata) {
    kalan += 1
    console.log(`KALDI  ${ad}\n       ${hata.message.split('\n')[0]}`)
    if (process.env.TANI) {
      for (const sayfa of baglam.pages()) {
        console.log(`       [tanı] sayfa hataları: ${JSON.stringify(sayfa.hatalar ?? [])}`)
        const metin = await sayfa.locator(BOLUM).innerText().catch(() => '(bölüm yok)')
        console.log(`       [tanı] ${metin.replace(/\s+/g, ' ').slice(0, 900)}`)
      }
    }
  } finally {
    await baglam.close()
  }
}
await tarayici.close()
sunucu.close()
console.log(`\n${senaryolar.filter((s) => !filtre || s.ad.includes(filtre)).length - kalan} geçti, ${kalan} kaldı`)
process.exit(kalan === 0 ? 0 : 1)
