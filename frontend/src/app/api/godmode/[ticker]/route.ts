import { NextRequest, NextResponse } from 'next/server'

// Bu route God Mode'un ADMIN_KEY'ini sunucu tarafinda tutar; tarayiciya ASLA sizmaz.
// Dashboard bu route'u cagirir, dogrudan God Mode servisine gitmez.
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ ticker: string }> }
) {
  const { ticker } = await params
  const godmodeUrl = process.env.GODMODE_URL || 'http://alphawise-godmode-execution:8000'
  const adminKey = process.env.GODMODE_ADMIN_KEY

  if (!adminKey) {
    return NextResponse.json(
      { error: 'God Mode admin anahtari sunucuda tanimli degil (GODMODE_ADMIN_KEY)' },
      { status: 503 }
    )
  }

  const ufuk = req.nextUrl.searchParams.get('ufuk') || '1'

  try {
    const resp = await fetch(
      `${godmodeUrl}/godmode/assessment/${encodeURIComponent(ticker.toUpperCase())}?ufuk=${encodeURIComponent(ufuk)}`,
      {
        headers: { 'x-admin-key': adminKey },
        signal: AbortSignal.timeout(90_000),
      }
    )
    const data = await resp.json()
    if (!resp.ok) {
      return NextResponse.json({ error: data.detail || 'God Mode servisi hata dondurdu' }, { status: resp.status })
    }
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json({ error: 'God Mode servisine ulasilamiyor: ' + err.message }, { status: 502 })
  }
}
