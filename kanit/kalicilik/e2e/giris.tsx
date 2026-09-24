// UÇTAN UCA DÜZENEK — GrafikTerminali'yi gerçek React + gerçek tarayıcı
// localStorage'ı ile, Next sunucusu olmadan çalıştırır. Yalnızca kanıt aracıdır;
// uygulama paketine girmez (bkz. kos.mjs).
//
// Ağ uçları sahte: bayrak AÇIK, kimlik ?kimlik= parametresinden, fiyat verisi
// deterministik bir TEST FİKSTÜRÜ (piyasa verisi değildir, hiçbir iddiada
// kullanılmaz — yalnızca grafiğin çizilecek bar bulması için).
import { createRoot } from 'react-dom/client'
import GrafikTerminali from '../../../frontend/components/GrafikTerminali'

function fiksturBarlari(): { date: string; open: string; high: string; low: string; close: string; volume: string }[] {
  const barlar = []
  let fiyat = 100
  const baslangic = Date.UTC(2025, 0, 2)
  for (let i = 0; i < 300; i += 1) {
    const gun = new Date(baslangic + i * 86_400_000)
    if (gun.getUTCDay() === 0 || gun.getUTCDay() === 6) continue
    const acilis = fiyat
    fiyat = fiyat + Math.sin(i / 7) * 1.5
    barlar.push({
      date: gun.toISOString().slice(0, 10),
      open: acilis.toFixed(2),
      high: (Math.max(acilis, fiyat) + 1).toFixed(2),
      low: (Math.min(acilis, fiyat) - 1).toFixed(2),
      close: fiyat.toFixed(2),
      volume: '1000',
    })
  }
  return barlar
}

const parametreler = new URLSearchParams(location.search)

window.fetch = async (girdi: RequestInfo | URL): Promise<Response> => {
  const adres = String(girdi)
  const json = (govde: unknown): Response =>
    new Response(JSON.stringify(govde), { status: 200, headers: { 'content-type': 'application/json' } })
  if (adres.includes('/api/config/grafik-flag')) return json({ enabled: true })
  if (adres.includes('/api/config/kimlik')) return json({ kullaniciId: parametreler.get('kimlik') ?? 'kullanici-A' })
  if (adres.includes('/api/market-data/')) return json({ data: fiksturBarlari() })
  return new Response('yok', { status: 404 })
}

const kok = createRoot(document.getElementById('kok') as HTMLElement)

/** Sürücü, bileşeni SÖKMEDEN prop değiştirebilsin diye (sembol/kullanıcı değişimi). */
function ciz(sembol: string, kimlik: string | undefined): void {
  kok.render(<GrafikTerminali symbol={sembol} kullaniciKimligi={kimlik} />)
}
;(window as unknown as { ciz: typeof ciz; sok: () => void }).ciz = ciz
;(window as unknown as { sok: () => void }).sok = () => kok.unmount()

ciz(parametreler.get('sembol') ?? 'AAPL', parametreler.get('prop') === '1' ? parametreler.get('kimlik') ?? undefined : undefined)
