import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

// Tek bir PDF raporu indirir.
//
// GUVENLIK — uc katmanli path traversal korumasi:
//   1. Ad deseni: yalnizca [A-Za-z0-9_-] + ".pdf". Bu desen "/", "\", ".."
//      ve gizli dosyalari (".env" gibi) zaten reddeder.
//   2. path.basename(): kalan her turlu dizin bileseni soyulur.
//   3. Cozulmus yolun rapor dizininin ICINDE kaldigi dogrulanir (realpath
//      ile sembolik bag kacisi da kapatilir).
// Ayrica dizin konteynere SALT OKUNUR baglanir.
const RAPOR_DIZINI = process.env.REPORTS_DIR || '/reports'
const GUVENLI_AD = /^[A-Za-z0-9][A-Za-z0-9_-]*\.pdf$/

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ dosya: string }> }
) {
  const { dosya } = await params

  // Katman 1 — desen kontrolu (URL cozulmesi sonrasi)
  let ad: string
  try {
    ad = decodeURIComponent(dosya)
  } catch {
    return NextResponse.json({ error: 'Gecersiz dosya adi' }, { status: 400 })
  }
  if (!GUVENLI_AD.test(ad)) {
    return NextResponse.json({ error: 'Gecersiz dosya adi' }, { status: 400 })
  }

  // Katman 2 — her turlu dizin bilesenini soy
  const guvenliAd = path.basename(ad)
  if (guvenliAd !== ad) {
    return NextResponse.json({ error: 'Gecersiz dosya adi' }, { status: 400 })
  }

  // Katman 3 — cozulmus yol rapor dizininin icinde mi
  const kokDizin = await fs.realpath(RAPOR_DIZINI).catch(() => path.resolve(RAPOR_DIZINI))
  const tamYol = path.resolve(kokDizin, guvenliAd)
  if (tamYol !== path.join(kokDizin, guvenliAd)) {
    return NextResponse.json({ error: 'Erisim reddedildi' }, { status: 403 })
  }

  try {
    // Sembolik bag ile disari cikilmadigini da dogrula
    const gercekYol = await fs.realpath(tamYol)
    if (!gercekYol.startsWith(kokDizin + path.sep)) {
      return NextResponse.json({ error: 'Erisim reddedildi' }, { status: 403 })
    }

    const bilgi = await fs.stat(gercekYol)
    if (!bilgi.isFile()) {
      return NextResponse.json({ error: 'Dosya bulunamadi' }, { status: 404 })
    }

    const icerik = await fs.readFile(gercekYol)
    return new NextResponse(new Uint8Array(icerik), {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Length': String(bilgi.size),
        'Content-Disposition': `attachment; filename="${guvenliAd}"`,
        'Cache-Control': 'no-store',
      },
    })
  } catch (err: any) {
    if (err?.code === 'ENOENT') {
      return NextResponse.json({ error: 'Dosya bulunamadi' }, { status: 404 })
    }
    return NextResponse.json({ error: 'Dosya okunamadi: ' + err.message }, { status: 500 })
  }
}
