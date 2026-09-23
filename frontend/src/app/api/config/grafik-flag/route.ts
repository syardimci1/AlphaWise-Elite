import { NextRequest, NextResponse } from 'next/server'

// Y7 — Feature Flag: grafik terminali. VARSAYILAN KAPALI.
//
// DESEN BILINCLI OLARAK koyfin-flag/route.ts ILE AYNI ve gerekcesi de ayni:
// NEXT_PUBLIC_ onekli bir degisken BUILD ZAMANINDA istemci paketine gomulurdu,
// yani kapatmak yeniden derleme + dagitim isterdi. Sunucu tarafinda her
// istekte process.env okunursa, degeri degistirip konteyneri yeniden
// baslatmak (rebuild YOK) yeterli olur — geri alma saniyeler surer.
//
// ONIZLEME TOKENI: ana bayrak kapaliyken bile ?grafik_preview=<token> ile
// yalnizca token'i bilen oturum ozelligi gorebilir. Dagitimdan sonraki ilk
// gozlem bu sekilde, son kullaniciya hic dokunmadan yapilir.
export async function GET(req: NextRequest) {
  const anaBayrak = process.env.GRAFIK_TERMINALI_ENABLED === '1'
  const onizlemeTokeni = process.env.GRAFIK_PREVIEW_TOKEN
  const istekTokeni = req.nextUrl.searchParams.get('grafik_preview')

  const onizlemeEslesti = Boolean(onizlemeTokeni) && istekTokeni === onizlemeTokeni

  return NextResponse.json(
    { enabled: anaBayrak || onizlemeEslesti, onizleme_modu: onizlemeEslesti && !anaBayrak },
    { headers: { 'Cache-Control': 'no-store' } }
  )
}
