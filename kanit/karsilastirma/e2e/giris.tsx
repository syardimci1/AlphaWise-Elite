// UÇTAN UCA DÜZENEK — karşılaştırma modu. GrafikTerminali'yi gerçek React + gerçek
// tarayıcı localStorage'ı ile, Next sunucusu olmadan çalıştırır. Yalnızca kanıt
// aracıdır; uygulama paketine girmez (bkz. kos.mjs).
//
// Ağ uçları SAHTE. Fiyat barları deterministik TEST FİKSTÜRLERİDİR (piyasa verisi
// değildir, hiçbir iddiada kullanılmaz). Semboller senaryoya göre adlandırılır:
//   MSFT   : ana fikstürle aynı günler, 100–104. işlem günleri EKSİK (5 gün)
//   NVDA   : 2 ay GEÇ başlar (ortak taban kayar)
//   PAHALI : ana fikstürün 1000 katı (farklı fiyat ölçeği)
//   HATA   : HTTP 500 · BOS: boş veri · UZAK: 2015 (ortak gün yok)
//   P*     : 2 yıl (Y10 ölçümü) · Q*: 1500 bar (üst sınır ölçümü)
import { createRoot } from 'react-dom/client'
import GrafikTerminali from '../../../frontend/components/GrafikTerminali'

type HamBar = { date: string; open: string; high: string; low: string; close: string; volume: string }

function fikstur(baslangic: number, takvimGunu: number, kaydirma: number, olcek: number, eksik: Set<number>): HamBar[] {
  const barlar: HamBar[] = []
  let fiyat = 100
  let islemGunu = 0
  for (let i = 0; i < takvimGunu; i += 1) {
    const gun = new Date(baslangic + i * 86_400_000)
    if (gun.getUTCDay() === 0 || gun.getUTCDay() === 6) continue
    const acilis = fiyat
    fiyat = fiyat + Math.sin((i + kaydirma) / 7) * 1.5
    if (!eksik.has(islemGunu)) {
      barlar.push({
        date: gun.toISOString().slice(0, 10),
        open: (acilis * olcek).toFixed(2),
        high: ((Math.max(acilis, fiyat) + 1) * olcek).toFixed(2),
        low: ((Math.min(acilis, fiyat) - 1) * olcek).toFixed(2),
        close: (fiyat * olcek).toFixed(2),
        volume: '1000',
      })
    }
    islemGunu += 1
  }
  return barlar
}

const OCAK_2025 = Date.UTC(2025, 0, 2)
const EKSIK_MSFT = new Set([100, 101, 102, 103, 104])

function sembolVerisi(sembol: string): { durum: number; govde: unknown } {
  if (sembol === 'HATA') return { durum: 500, govde: { hata: 'sahte' } }
  if (sembol === 'BOS') return { durum: 200, govde: { data: [] } }
  if (sembol === 'UZAK') return { durum: 200, govde: { data: fikstur(Date.UTC(2015, 0, 2), 60, 0, 1, new Set()) } }
  if (sembol === 'MSFT') return { durum: 200, govde: { data: fikstur(OCAK_2025, 300, 40, 3, EKSIK_MSFT) } }
  if (sembol === 'NVDA') return { durum: 200, govde: { data: fikstur(Date.UTC(2025, 2, 3), 241, 90, 1.4, new Set()) } }
  if (sembol === 'PAHALI') return { durum: 200, govde: { data: fikstur(OCAK_2025, 300, 0, 1000, new Set()) } }
  if (sembol.startsWith('P')) {
    return { durum: 200, govde: { data: fikstur(Date.UTC(2024, 0, 2), 730, sembol.length * 13, 1, new Set()) } }
  }
  if (sembol.startsWith('Q')) {
    return { durum: 200, govde: { data: fikstur(Date.UTC(2020, 0, 2), 2100, sembol.length * 13, 1, new Set()).slice(-1500) } }
  }
  return { durum: 200, govde: { data: fikstur(OCAK_2025, 300, 0, 1, new Set()) } }
}

const parametreler = new URLSearchParams(location.search)
const istekler: string[] = []
;(window as unknown as { istekler: string[] }).istekler = istekler

window.fetch = async (girdi: RequestInfo | URL): Promise<Response> => {
  const adres = String(girdi)
  const json = (govde: unknown, durum = 200): Response =>
    new Response(JSON.stringify(govde), { status: durum, headers: { 'content-type': 'application/json' } })
  if (adres.includes('/api/config/grafik-flag')) return json({ enabled: true })
  if (adres.includes('/api/config/kimlik')) return json({ kullaniciId: parametreler.get('kimlik') ?? 'kullanici-A' })
  const eslesme = /\/api\/market-data\/([^?]+)/.exec(adres)
  if (eslesme !== null) {
    const sembol = decodeURIComponent(eslesme[1])
    istekler.push(sembol)
    const { durum, govde } = sembolVerisi(sembol)
    return json(govde, durum)
  }
  return new Response('yok', { status: 404 })
}

const kok = createRoot(document.getElementById('kok') as HTMLElement)
function ciz(sembol: string): void {
  kok.render(<GrafikTerminali symbol={sembol} />)
}
;(window as unknown as { ciz: typeof ciz }).ciz = ciz
ciz(parametreler.get('sembol') ?? 'AAPL')
