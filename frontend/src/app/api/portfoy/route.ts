import { NextRequest } from 'next/server'
import { istekKimligi, servisProxy } from '@/lib/servis-proxy'

// Portfoy performans serisi (Madde 30). Ticker almaz; defterin tamamidir.
export async function GET(req: NextRequest) {
  return servisProxy({
    taban: process.env.PORTFOY_URL || 'http://alphawise-portfoy:8000',
    yol: '/performans',
    zamanAsimiMs: 30_000,
    servisAdi: 'Portföy performansı',
    kimlik: istekKimligi(req),
  })
}
