import { NextRequest, NextResponse } from 'next/server'

// BIST Arastirma Masasi - AlphaWise'in ana ticari sisteminden (God Mode/MAA)
// TAMAMEN AYRI, izole bir Docker agindaki salt-okunur arastirma servisine
// proxy. Bu servis hicbir emir gondermez, ADMIN_KEY gerektirmez.
export async function POST(req: NextRequest) {
  const bistUrl = process.env.BIST_DESK_URL || 'http://bist-research-desk:8000'

  let govde: any
  try {
    govde = await req.json()
  } catch {
    return NextResponse.json({ error: 'Gecersiz istek govdesi (JSON bekleniyor)' }, { status: 400 })
  }

  if (!govde?.tickerlar || !Array.isArray(govde.tickerlar) || govde.tickerlar.length === 0) {
    return NextResponse.json({ error: 'En az bir ticker gerekli (tickerlar alani)' }, { status: 400 })
  }

  try {
    const resp = await fetch(`${bistUrl}/arastir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(govde),
      signal: AbortSignal.timeout(60_000),
    })
    const data = await resp.json()
    if (!resp.ok) {
      return NextResponse.json({ error: data.detail || 'BIST Arastirma Masasi servisi hata dondurdu' }, { status: resp.status })
    }
    return NextResponse.json(data)
  } catch (err: any) {
    return NextResponse.json({ error: 'BIST Arastirma Masasi servisine ulasilamiyor: ' + err.message }, { status: 502 })
  }
}
