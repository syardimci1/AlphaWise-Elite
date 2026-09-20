// ============================================================================
// RAPOR ERİŞİMİ — dizin sözleşmesi ve rol kapısı, TEK KAYNAKTAN
// ============================================================================
//
// NEDEN AYRI DOSYA: `RAPOR_DIZINI` ve `GUVENLI_AD` iki ayrı rotada
// KOPYALANMIŞTI (listeleme ve indirme). Kopya sözleşmeler sessizce ayrışır:
// biri sıkılaştırılıp öteki unutulursa listede görünmeyen bir dosya yine de
// indirilebilir hâle gelir. Tek kaynak bunu yapısal olarak imkânsız kılar.
//
// ----------------------------------------------------------------------------
// NEDEN ROL KAPISI VAR — ÖLÇÜLDÜ (17.09.2026), VARSAYILMADI
// ----------------------------------------------------------------------------
// Bu dizindeki belgelerde KULLANICI VERİSİ YOK. Doğrulandı: portföy/pozisyon/
// emir/karar-geçmişi araması (`pozisyon acildi|acik pozisyon|portfoy degeri|
// adet=`) üç `.md` dosyasında da **0** eşleşme verdi. Yani bu bir
// çapraz-kullanıcı sızıntısı DEĞİLDİR ve kullanıcı bazlı dizine bölmek
// YANLIŞ çözüm olurdu.
//
// Ama içerik zararsız da değil — belgelerde ölçülen şunlar var:
//   * `gunsonu_raporu_2026-08-21.md:488+` — 33 servisin tam envanteri, her
//     biri İÇ PORT numarasıyla (news-monitor 8100, cognee 8130, gamma 8220 …).
//   * `:522+` "Bilinen riskler" tablosu — KAPATILMAMIŞ açıkları adıyla
//     listeliyor: "`isyatirimhisse` TLS sertifika doğrulamasını kapatıyor |
//     Ortadaki adam saldırısına teorik açıklık | **Bilinen, çözülmemiş**".
//   * Kalibrasyon katsayıları, λ=0 gerekçesi, LLMQuant kredi olguları.
//
// Yani sınıf: KULLANICI-GİZLİ değil, SİSTEM-GİZLİ.
//
// Bugün fiilî sızıntı sıfır (Supabase'deki iki hesap da iç: admin + partner).
// AMA yarın değil — ölçüldü:
//   * `db/migrations/004:58` → `role public.user_role DEFAULT 'user' NOT NULL`
//   * `005`'teki `yeni_kullanici_profili_olustur()` tetiği `role`'ü HİÇ SET
//     ETMİYOR (canlı doğrulandı: fonksiyon gövdesinde 'role' geçmiyor).
// Dolayısıyla kaydolan İLK GERÇEK MÜŞTERİ `role='user'` ile açılır ve
// kısıt olmadan yukarıdakilerin tamamını indirebilirdi.

import { promises as fs } from 'fs'
import path from 'path'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { rolKapisi, rolKarari, izinliRoller, type Rol } from './rol'

// `rolKarari` 20.09.2026'da `rol.ts`'e taşındı (ikinci bir uç aynı karara
// ihtiyaç duydu). Buradan yeniden dışa aktarılıyor ki mevcut çağıranlar ve
// testler etkilenmesin; tanım artık TEK yerde.
export { rolKarari }

/** Dizin konteynere SALT OKUNUR bağlanır; bu rotalar hiçbir koşulda yazmaz. */
export const RAPOR_DIZINI = process.env.REPORTS_DIR || '/reports'

/**
 * Yalnızca bu desene uyan dosya adları kabul edilir. Yol ayıracı (`/`, `\`),
 * nokta-nokta (`..`) ve gizli dosyalar bu desenle zaten dışarıda kalır.
 */
export const GUVENLI_AD = /^[A-Za-z0-9][A-Za-z0-9_-]*\.pdf$/

/**
 * VARSAYILAN İZİN LİSTESİ: `admin,partner`.
 *
 * Bu seçim SIFIR REGRESYON içindir — bugünkü iki hesabın ikisi de erişimini
 * aynen korur. `RAPOR_IZINLI_ROLLER` ortam değişkeniyle daraltılabilir.
 *
 * ⚠ ÜRÜN KARARI: `partner` dış bir iş ortağıysa, yukarıda listelenen
 * kapatılmamış güvenlik açıkları ve iç port envanteri göz önüne alınarak
 * bu değer `admin` olarak daraltılmalıdır. Kod her iki durumda aynıdır;
 * değişen tek şey ortam değişkenidir.
 */
const VARSAYILAN_ROLLER: Rol[] = ['admin', 'partner']

export function raporRolleri(): Rol[] {
  return izinliRoller(process.env.RAPOR_IZINLI_ROLLER, VARSAYILAN_ROLLER)
}

/**
 * Rapor rol kapısı. İzin varsa `null`, yoksa doğrudan döndürülecek bir yanıt.
 *
 * Kapı, dosya sistemine dokunmadan ÖNCE çağrılmalıdır: yetkisiz bir çağırana
 * dizinin dolu mu boş mu olduğu hakkında zamanlama üzerinden bilgi sızmasın.
 */
export async function raporKapisi(req: NextRequest): Promise<NextResponse | null> {
  return rolKapisi(
    req,
    raporRolleri(),
    'Bu belgelere erisim yetkiniz yok',
    'Raporlar sistem belgeleridir ve yalnizca yetkili rollere aciktir.',
  )
}

/** Rapor dizinini güvenli biçimde çözer (sembolik bağ kaçışı dahil). */
export async function kokDizinCoz(): Promise<string> {
  return fs.realpath(RAPOR_DIZINI).catch(() => path.resolve(RAPOR_DIZINI))
}
