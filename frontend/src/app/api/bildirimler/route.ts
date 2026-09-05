import { NextRequest } from 'next/server'
import { servisProxy } from '@/lib/servis-proxy'

// Bildirim merkezi (Madde 28). Ticker almaz; sistem geneli alarm ozetidir.
export async function GET(_req: NextRequest) {
  return servisProxy({
    taban: process.env.BILDIRIM_URL || 'http://alphawise-bildirim:8000',
    yol: '/bildirimler?azami=40',
    zamanAsimiMs: 15_000,
    servisAdi: 'Bildirim merkezi',
  })
}
