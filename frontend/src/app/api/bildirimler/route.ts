import { NextRequest } from 'next/server'
import { istekKimligi, servisProxy } from '@/lib/servis-proxy'

// Bildirim merkezi (Madde 28). Ticker almaz; sistem geneli alarm ozetidir.
export async function GET(req: NextRequest) {
  return servisProxy({
    taban: process.env.BILDIRIM_URL || 'http://alphawise-bildirim:8000',
    yol: '/bildirimler?azami=40',
    zamanAsimiMs: 15_000,
    servisAdi: 'Bildirim merkezi',
    kimlik: istekKimligi(req),
  })
}
