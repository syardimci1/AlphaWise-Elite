import { createServerClient } from '@supabase/ssr'
import { NextRequest, NextResponse } from 'next/server'

// ============================================================================
// SUNUCU TARAFI OTURUM DOGRULAMA — 23.08.2026
//
// NEDEN: Denetimde olculdu — /api altindaki 13 route'un HICBIRINDE kimlik
// dogrulamasi yoktu. Kimlik kontrolu YALNIZCA tarayicida yapiliyordu
// (dashboard/page.tsx: supabase.auth.getUser() -> yoksa '/' sayfasina yollar).
// Bu, KULLANICI ARAYUZUNU gizler ama VERIYI gizlemez: /api/... uclarina
// dogrudan yapilan bir istek oturum olmadan da 200 donuyordu.
//
// BU KATMAN NEYI COZER / NEYI COZMEZ:
//   COZER : /api/* altindaki her uca, dogrulanmis bir Supabase oturumu
//           zorunlulugu getirir (middleware'de, tek noktadan).
//   COZMEZ: ic servislerin (MAA:8000, godmode vb.) KENDI kimlik dogrulamasi
//           yoktur. Onlara Docker ic agindan hala kimliksiz ulasilabilir.
//           Bugun kabul edilebilir, cunku hicbir servis 0.0.0.0'a bagli
//           degil (olculdu: tum yayinlar 127.0.0.1'e sabitli).
//
// COKLU URL TUZAGI (olcum ile bulundu):
// supabase-js cerez/depolama anahtarini URL'in ILK host etiketinden turetiyor:
//   `sb-${hostname.split('.')[0]}-auth-token`
// Tarayici NEXT_PUBLIC_SUPABASE_URL (http://localhost:8020) kullandigi icin
// cerez adi `sb-localhost-auth-token`. Sunucu tarafi ise ayni adrese
// ulasamaz (konteynerin kendi localhost'u) ve ic adresi kullanmak ZORUNDA:
// http://supabase-kong:8000. Ic adresle kurulan istemci ise cerezi
// `sb-supabase-kong-auth-token` adiyla ARAR ve HICBIR oturumu bulamaz —
// yani her istek 401 olurdu. Bu yuzden ag adresi IC, cerez adi GENEL
// url'den turetilir. cerezAdi() bu turetmenin birebir kopyasidir
// (supabase-js: SupabaseClient.js -> `sb-${baseUrl.hostname.split('.')[0]}
// -auth-token`) ve dogrulugu canli uctan uca testle kanitlanmistir:
// gercek oturum cerezi 200, cerezsiz istek 401.
// ============================================================================

const GENEL_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const ANON = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
// Sunucu tarafi ag adresi. Ortam degiskeni yoksa Docker ic DNS adi kullanilir.
const IC_URL = process.env.SUPABASE_INTERNAL_URL || 'http://supabase-kong:8000'

// Supabase'in askida kalmasi tum dashboard'i kilitlemesin diye ust sinir.
const DOGRULAMA_ZAMAN_ASIMI_MS = 5000

/** supabase-js'in cerez adi turetmesinin birebir kopyasi. */
export function cerezAdi(genelUrl: string): string {
  return `sb-${new URL(genelUrl).hostname.split('.')[0]}-auth-token`
}

const CEREZ_ADI = GENEL_URL ? cerezAdi(GENEL_URL) : ''

/**
 * AGA CIKMADAN yapilan on eleme: oturum cerezi hic YOK MU?
 *
 * Neden ayri bir adim: dogrulama Supabase'e HTTP istegi demek. Cerezi hic
 * olmayan (yani kimliksiz) bir istek selini once buradan cevirmezsek, kendi
 * kimlik sunucumuza yonelen bir yuk buyutecine donusur. Bu kontrol bedava.
 *
 * @supabase/ssr buyuk oturumlari `<ad>.0`, `<ad>.1` diye parcali cerezlere
 * bolebildigi icin onek eslesmesi de kabul edilir.
 */
export function oturumCereziVarMi(req: NextRequest): boolean {
  if (!CEREZ_ADI) return false
  return req.cookies
    .getAll()
    .some((c) => c.name === CEREZ_ADI || c.name.startsWith(`${CEREZ_ADI}.`))
}

export type OturumSonuc = {
  gecerli: boolean
  sebep: 'ok' | 'yapilandirma_eksik' | 'gecersiz_oturum' | 'dogrulama_hatasi'
  kullaniciId?: string
}

/**
 * Cerezdeki erisim jetonunu Supabase'e DOGRULATIR.
 *
 * Neden sadece "cerez var mi" yetmez: cerez istemci tarafindan yazilabilir.
 * Imzasi gecersiz ya da suresi dolmus bir jeton da cerez olarak gorunur.
 * getUser() jetonu kimlik sunucusuna dogrulatir; imza/sure kontrolu orada
 * yapilir.
 *
 * HATA DURUMUNDA KAPALI (fail-closed): Supabase'e ulasilamazsa istek
 * REDDEDILIR. Acik birakmak (fail-open), kimlik sunucusunu dusurebilen
 * birine tum uclari acardi. Ayni tercih hiz sinirlayicida da yapilmisti.
 */
export async function oturumDogrula(
  req: NextRequest,
  yanit: NextResponse,
): Promise<OturumSonuc> {
  if (!GENEL_URL || !ANON) return { gecerli: false, sebep: 'yapilandirma_eksik' }

  const sb = createServerClient(IC_URL, ANON, {
    cookies: {
      getAll: () => req.cookies.getAll(),
      setAll: (liste) => {
        // Jeton tazelenirse yeni cerezler yanita yazilir; boylece oturum
        // middleware yuzunden dusmez.
        liste.forEach(({ name, value, options }) =>
          yanit.cookies.set(name, value, options),
        )
      },
    },
    cookieOptions: { name: CEREZ_ADI },
    global: {
      fetch: (girdi: RequestInfo | URL, secenek?: RequestInit) =>
        fetch(girdi, {
          ...secenek,
          signal: AbortSignal.timeout(DOGRULAMA_ZAMAN_ASIMI_MS),
        }),
    },
  })

  try {
    const { data, error } = await sb.auth.getUser()
    if (error || !data?.user) return { gecerli: false, sebep: 'gecersiz_oturum' }
    return { gecerli: true, sebep: 'ok', kullaniciId: data.user.id }
  } catch {
    return { gecerli: false, sebep: 'dogrulama_hatasi' }
  }
}
