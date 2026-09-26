// FAZ 1 SONDASI — lightweight-charts 5.2.1 çizgi serisinde eksik gün nasıl çizilir?
//
// Soru (Y9/C4): bir sembolün barı olmayan günde (diğer sembolde var) çizgi
//   (a) veri dizisinden o gün HİÇ verilmezse,
//   (b) o gün `{ time }` (whitespace) olarak verilirse
// kesiliyor mu, yoksa komşu iki nokta düz çizgiyle birleştiriliyor mu (= görsel enterpolasyon)?
// Ölçüm: eksik günün x koordinatındaki sütunda serinin renginde piksel var mı.
//
// ÇALIŞTIRMA: PLAYWRIGHT_CORE=<...>/playwright-core/index.js CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
//   node kanit/karsilastirma/e2e/bosluk_sondasi.mjs
import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const burasi = dirname(fileURLToPath(import.meta.url))
const lwc = readFileSync(resolve(burasi, '../../../frontend/node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.js'))
const pw = await import(process.env.PLAYWRIGHT_CORE ?? 'playwright-core')
const chromium = pw.chromium ?? pw.default.chromium

const html = `<!doctype html><body style="margin:0;background:#0f172a"><div id="k" style="width:800px;height:300px"></div>
<script src="/lwc.js"></script><script>
const gunler = []; for (let i = 1; i <= 21; i++) gunler.push('2026-03-' + String(i).padStart(2, '0'))
const EKSIK = '2026-03-11'
window.olc = (kip) => {
  document.getElementById('k').innerHTML = ''
  const g = LightweightCharts.createChart(document.getElementById('k'), { width: 800, height: 300,
    layout: { background: { color: '#0f172a' }, textColor: '#fff' }, grid: { vertLines: { visible: false }, horzLines: { visible: false } } })
  const tam = g.addSeries(LightweightCharts.LineSeries, { color: '#0000ff', lineWidth: 2, lastValueVisible: false, priceLineVisible: false })
  const eksik = g.addSeries(LightweightCharts.LineSeries, { color: '#ff0000', lineWidth: 3, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false })
  tam.setData(gunler.map((t, i) => ({ time: t, value: 10 + i * 0.1 })))
  const veri = []
  for (const t of gunler) {
    if (t === EKSIK) { if (kip !== 'atlanmis') veri.push({ time: t }); continue }
    const nokta = { time: t, value: 50 }
    // 'renk-sonraki': boşluktan SONRAKİ ilk noktanın rengi saydam; 'renk-onceki': boşluktan ÖNCEKİ son noktanın.
    if (kip === 'renk-sonraki' && t === '2026-03-12') nokta.color = 'rgba(0,0,0,0)'
    if (kip === 'renk-onceki' && t === '2026-03-10') nokta.color = 'rgba(0,0,0,0)'
    veri.push(nokta)
  }
  eksik.setData(veri)
  g.timeScale().fitContent()
  return new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => {
    const x = Math.round(g.timeScale().timeToCoordinate(EKSIK))
    const kanvas = g.takeScreenshot(true)
    const ctx = kanvas.getContext('2d'); const oran = kanvas.width / 800
    const say = (sutun) => {
      const veriPx = ctx.getImageData(Math.round(sutun * oran), 0, 1, kanvas.height).data
      let kirmizi = 0
      for (let i = 0; i < veriPx.length; i += 4) if (veriPx[i] > 200 && veriPx[i + 1] < 60 && veriPx[i + 2] < 60) kirmizi++
      return kirmizi
    }
    const xAt = (t) => g.timeScale().timeToCoordinate(t)
    // Ölçülen sütunlar: 09→10 arası (boşluk öncesi segment), 10→11 ve 11→12 (boşluğu köprüleyen segment), 12→13 (sonrası)
    const orta = (a, b) => (xAt(a) + xAt(b)) / 2
    r({ kip, x,
      once_09_10: say(orta('2026-03-09', '2026-03-10')),
      kopru_10_11: say(orta('2026-03-10', EKSIK)),
      eksikGun_11: say(x),
      kopru_11_12: say(orta(EKSIK, '2026-03-12')),
      sonra_12_13: say(orta('2026-03-12', '2026-03-13')) })
  })))
}
</script>`
const sunucu = createServer((i, y) => {
  if (i.url === '/lwc.js') { y.writeHead(200, { 'content-type': 'text/javascript' }); y.end(lwc); return }
  y.writeHead(200, { 'content-type': 'text/html' }); y.end(html)
})
await new Promise((t) => sunucu.listen(0, '127.0.0.1', t))
const tarayici = await chromium.launch({ executablePath: process.env.CHROMIUM, headless: true })
const sayfa = await tarayici.newPage()
await sayfa.goto(`http://127.0.0.1:${sunucu.address().port}/`)
for (const kip of ['atlanmis', 'whitespace', 'renk-onceki', 'renk-sonraki']) console.log(JSON.stringify(await sayfa.evaluate((k) => window.olc(k), kip)))
await tarayici.close(); sunucu.close()
