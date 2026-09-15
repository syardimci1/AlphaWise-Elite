import { NextRequest, NextResponse } from 'next/server'

// C5 - Feature Flag: koyfin_event_overlay.
//
// NEDEN NEXT_PUBLIC_ ORTAM DEGISKENI DEGIL: NEXT_PUBLIC_ onekli
// degiskenler BUILD ZAMANINDA istemci paketine gomulur - kapatmak
// yeniden derleme+dagitim gerektirirdi. Bu, Y5 (atomik geri alinabilirlik)
// ve Faz 5 kill-switch hedefiyle ("10sn icinde kapanir") CELISIR. Bu
// yuzden sunucu tarafinda, HER ISTEKTE process.env okunan bir route:
// deger degistirip konteyneri `docker compose up -d` (rebuild YOK,
// yalnizca yeniden baslatma) ile guncellemek yeterli.
//
// Beyaz liste (Faz 5 on-kosul kontrolu - gercek canary altyapisi
// yoksa "yumusak acilis" esdegeri): ?koyfin_preview=<token> ana bayraktan
// BAGIMSIZ olarak true doner, boylece dagitim sonrasi ilk gozlem
// yalnizca bu token'i bilen oturumda yapilabilir.
export async function GET(req: NextRequest) {
  const anaBayrak = process.env.KOYFIN_EVENT_OVERLAY_ENABLED === '1'
  const onizlemeTokeni = process.env.KOYFIN_PREVIEW_TOKEN
  const istekTokeni = req.nextUrl.searchParams.get('koyfin_preview')

  const onizlemeEslesti = Boolean(onizlemeTokeni) && istekTokeni === onizlemeTokeni

  return NextResponse.json(
    { enabled: anaBayrak || onizlemeEslesti, onizleme_modu: onizlemeEslesti && !anaBayrak },
    { headers: { 'Cache-Control': 'no-store' } }
  )
}
