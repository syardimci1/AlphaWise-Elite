import { NextRequest } from 'next/server'
import { servisProxy } from '@/lib/servis-proxy'

// Portfoy performans serisi (Madde 30). Ticker almaz; defterin tamamidir.
export async function GET(_req: NextRequest) {
  return servisProxy({
    taban: process.env.PORTFOY_URL || 'http://alphawise-portfoy:8000',
    yol: '/performans',
    zamanAsimiMs: 30_000,
    servisAdi: 'Portföy performansı',
  })
}
