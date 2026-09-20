// ============================================================================
// ROL OKUMA — `public.profiles.role` sunucu tarafında, kullanıcının KENDİ
// oturumuyla okunur.
// ============================================================================
//
// NEDEN SUNUCU TARAFINDA VE KULLANICININ KENDİ OTURUMUYLA:
// 006 göçü `profiles` üzerinde RLS'i sertleştirdi — `authenticated` yalnızca
// KENDİ satırını görür (`auth.uid() = id`) ve `anon` hiçbir şey göremez.
// Canlı doğrulandı (17.09.2026): authenticated rolüyle açılan bir oturumda
// `SELECT role FROM public.profiles WHERE id=<kendi>` → 'admin' döndü.
// Yani servis anahtarı (service_role) GEREKMEZ; kullanıcının kendi jetonu
// yeter ve yetki sınırı veritabanı tarafından zorlanır.
//
// MALİYET: rol okuması Supabase'e bir sorgu demektir. Bu yüzden middleware'de
// DEĞİL, yalnızca rol kapısına ihtiyaç duyan uçlarda (bugün raporlar, 'ucuz'
// hız sınıfı) çağrılır. Middleware'e koymak TÜM /api trafiğine bir ağ çağrısı
// eklerdi — dosyanın "ucuz-önce/pahalı-sonra" ilkesine aykırı olurdu.
//
// FAIL-CLOSED: rol okunamazsa (oturum yok, satır yok, ağ hatası) `null` döner
// ve çağıran ERİŞİMİ REDDETMELİDİR. Burada "bilinmiyorsa izin ver" yoktur.

import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { cerezAdi } from './oturum'

const GENEL_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const ANON = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const IC_URL = process.env.SUPABASE_INTERNAL_URL || 'http://supabase-kong:8000'
const CEREZ_ADI = GENEL_URL ? cerezAdi(GENEL_URL) : ''

// Supabase askıda kalırsa rapor ucu tüm dashboard'ı kilitlemesin.
const ROL_ZAMAN_ASIMI_MS = 5000

export type Rol = 'user' | 'partner' | 'admin'

const GECERLI_ROLLER: readonly string[] = ['user', 'partner', 'admin']

/**
 * Çağıran kullanıcının rolünü okur. Okunamazsa `null` — çağıran reddetmelidir.
 */
export async function rolOku(req: NextRequest): Promise<Rol | null> {
  if (!GENEL_URL || !ANON) return null
  try {
    const sb = createServerClient(IC_URL, ANON, {
      cookies: {
        getAll: () => req.cookies.getAll(),
        // Bu yol yalnızca OKUR; çerez tazeleme middleware'in işidir ve
        // burada yazmaya kalkmak yanıt nesnesi olmadığı için anlamsızdır.
        setAll: () => {},
      },
      cookieOptions: { name: CEREZ_ADI },
      global: {
        fetch: (girdi: RequestInfo | URL, secenek?: RequestInit) =>
          fetch(girdi, { ...secenek, signal: AbortSignal.timeout(ROL_ZAMAN_ASIMI_MS) }),
      },
    })
    // RLS zaten "yalnızca kendi satırı" diyor; yine de açıkça tek satır isteniyor.
    const { data, error } = await sb.from('profiles').select('role').single()
    if (error || !data) return null
    const ham = String((data as any).role ?? '')
    return GECERLI_ROLLER.includes(ham) ? (ham as Rol) : null
  } catch {
    return null
  }
}

/**
 * Rol izin listesini çözer.
 *
 * Ortam değişkeniyle daraltılabilir olması bilinçli: içeriğin kime açılacağı
 * bir ÜRÜN kararıdır ve kod değişikliği gerektirmemelidir.
 */
export function izinliRoller(ham: string | undefined, varsayilan: Rol[]): Rol[] {
  if (!ham) return varsayilan
  const ayiklanan = ham
    .split(',')
    .map(r => r.trim().toLowerCase())
    .filter((r): r is Rol => GECERLI_ROLLER.includes(r))
  // Boş/bozuk yapılandırma sessizce "herkese açık"a dönüşmemeli:
  // hiçbir geçerli rol ayıklanamadıysa varsayılana DÜŞÜLÜR, izin verilmez.
  return ayiklanan.length > 0 ? ayiklanan : varsayilan
}

/**
 * SAF karar fonksiyonu — test edilebilirlik için ağdan ayrılmıştır.
 * `rol` null ise (okunamadı) erişim REDDEDİLİR: fail-closed.
 *
 * 20.09.2026'da `raporlar.ts`'ten BURAYA taşındı. Gerekçe: ikinci bir uç
 * (bildirimler) aynı karara ihtiyaç duydu ve güvenlik kararının iki kopyası
 * sessizce ayrışır — biri sıkılaştırılıp öteki unutulur. `raporlar.ts` onu
 * yeniden dışa aktarmayı sürdürüyor, böylece mevcut çağıranlar etkilenmedi.
 */
export function rolKarari(rol: Rol | null, izinli: Rol[]): boolean {
  if (!rol) return false
  return izinli.includes(rol)
}

/**
 * GENEL rol kapısı. İzin varsa `null`, yoksa doğrudan döndürülecek yanıt.
 *
 * Kapı, korunan kaynağa (dosya sistemi, aşağı akış servisi) dokunmadan ÖNCE
 * çağrılmalıdır: yetkisiz bir çağırana kaynağın durumu hakkında zamanlama
 * üzerinden bilgi sızmasın.
 *
 * Sebep DIŞARIYA ayrıntılı verilmez ("rol okunamadı" ile "rolün yetmiyor"
 * ayrımı çağırana bilgi olur); teşhis için `X-Rol` başlığında tutulur.
 */
export async function rolKapisi(
  req: NextRequest,
  izinli: Rol[],
  hata: string,
  detay: string,
): Promise<NextResponse | null> {
  const rol = await rolOku(req)
  if (rolKarari(rol, izinli)) return null
  return NextResponse.json(
    { hata, detay },
    { status: 403, headers: { 'X-Rol': rol ?? 'okunamadi' } },
  )
}
