// ============================================================================
// KİRACI SÖZLEŞMESİ — başlık adları ve kimlik okuma, TEK KAYNAKTAN
// ============================================================================
//
// NEDEN AYRI BİR DOSYA:
// 16.09.2026 tutarlılık denetiminde ölçüldü ki iki ayrı spesifikasyon aynı
// sabiti (KULLANICI_BASLIGI) farklı değerlerle tanımlıyordu: middleware
// 'x-kullanici-id' yazarken tüketici 'x-alphawise-kullanici' okuyordu.
// İkisi de KENDİ testinden geçiyordu ama zincir hiçbir hata vermeden
// kopuyordu — süzgeç asla devreye girmiyor, ham hata gövdeleri kullanıcıya
// gitmeye devam ediyordu. Tek kaynak bu hatayı DERLEME ZAMANINA taşır:
// ad sapması artık sessiz bir hiç değil, bir tip hatasıdır.
//
// ----------------------------------------------------------------------------
// GÜVEN MODELİ — BU BAŞLIKLAR BİR YETKİ BELGESİ DEĞİLDİR
// ----------------------------------------------------------------------------
// Buradaki başlıklar YALNIZCA frontend middleware'i ile yukarı akış servis
// arasındaki iç ağda anlamlıdır ve güvenilirlikleri iki varsayıma bağlıdır:
//
//   (V1) Servis portları dışarıdan erişilemez. ÖLÇÜLDÜ (16.09.2026):
//        frontend 127.0.0.1:3000'e, MAA 127.0.0.1:8005'e bağlı; diğer
//        servisler yalnızca docker iç ağında.
//   (V2) İç ağdaki her süreç güvenilirdir.
//
// V2 bugün ZAYIF bir varsayımdır: cron betikleri frontend'e hiç uğramadan
// doğrudan servis portlarına gidiyor. Yani ağdaki bir süreç bu başlığı
// istediği değerle gönderebilir.
//
// Bu yüzden başlıklar ŞUNLAR İÇİN kullanılabilir:
//   ✅ atfetme ("kim tetikledi"), günlükleme, kota MUHASEBESİ, önbellek ayırma
// ŞUNLAR İÇİN KULLANILAMAZ:
//   ❌ yetkilendirme, erişim kontrolü, "bu kullanıcı bu veriyi görebilir mi"
// Yetkilendirme kararı her zaman doğrulanmış oturuma (oturumDogrula) ya da
// veritabanı düzeyinde RLS'e dayanmalıdır.
//
// ----------------------------------------------------------------------------
// KİMLİK YOKLUĞU POLİTİKASI — kalem bazındadır, tek global kural YANLIŞTIR
// ----------------------------------------------------------------------------
//   A) ATFETME/SÜZME amaçlı tüketiciler (servis proxy'sinin hata süzgeci,
//      kota sayacı): kimlik yoksa `sistem` kiracısı varsayılır ve BUGÜNKÜ
//      davranış sürer. Gerekçe: bu yollarda kimliğin yokluğu bir veri açığa
//      çıkması üretmez, yalnızca atfetme kaybı üretir; fail-closed yapmak
//      çalışan otomasyonu durdururdu.
//   B) AYIRMA amaçlı tüketiciler (kullanıcıya özel dizin/önbellek): kimlik
//      yoksa FAIL-CLOSED — çünkü burada kimliğin yokluğu doğrudan "yanlış
//      kiracının verisini ver" anlamına gelir.

import type { NextRequest } from 'next/server'

/** Aşağı akışa geçirilen kullanıcı kimliği (Supabase auth.users.id ya da SISTEM_KIRACI). */
export const KULLANICI_BASLIGI = 'x-kullanici-id'

/** Çağıranın TÜRÜ. Kimlikten AYRI bir kavramdır: "kim" değil, "ne tür çağıran". */
export const KIRACI_BASLIGI = 'x-kiraci-sinifi'

/** JWT taşımayan iç çağıranlar için kiracı adı. */
export const SISTEM_KIRACI = 'sistem'

export type KiraciSinifi = 'kullanici' | 'sistem'

export type Kimlik = {
  /** Supabase kullanıcı UUID'si, ya da SISTEM_KIRACI. */
  kullaniciId: string
  kiraci: KiraciSinifi
}

// Kabul edilen kimlik biçimi: Supabase UUID ya da tam olarak 'sistem'.
// DAR TUTULDU: bu değer ileride dosya yolu ve Redis anahtarı üretiminde
// kullanılacak; serbest metin kabul etmek yol aşımı ve anahtar enjeksiyonu
// yüzeyi açardı.
const UUID_DESENI =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

/** Değer geçerli bir kimlik mi? Değilse null döner — sessizce düzeltmez. */
export function kimlikDogrula(ham: string | null | undefined): string | null {
  if (!ham) return null
  const d = ham.trim()
  if (d === SISTEM_KIRACI) return SISTEM_KIRACI
  return UUID_DESENI.test(d) ? d.toLowerCase() : null
}

/**
 * Gelen istekten kiraci başlıklarını KOŞULSUZ siler ve temiz bir başlık
 * kümesi döndürür.
 *
 * NEDEN KOŞULSUZ: istemci bu başlıkları kendisi gönderebilir. Middleware
 * her yolda kendi değerini yazsa bile, yazmadığı BİR dal kalırsa (örneğin
 * sınıfı olmayan bir yol) istemcinin uydurduğu değer aşağı akışa geçerdi.
 * Silme işlemi bu yüzden dallanmadan ÖNCE ve koşulsuz yapılır.
 */
export function basliklariTemizle(req: NextRequest): Headers {
  const b = new Headers(req.headers)
  b.delete(KULLANICI_BASLIGI)
  b.delete(KIRACI_BASLIGI)
  return b
}

/**
 * Aşağı akış tüketicisi için kimliği okur.
 *
 * Dönüş `null` ise çağıran, yukarıdaki politikanın A mı B mi olduğuna göre
 * karar vermelidir — bu fonksiyon o kararı VERMEZ.
 */
export function kimlikOku(basliklar: Headers): Kimlik | null {
  const kullaniciId = kimlikDogrula(basliklar.get(KULLANICI_BASLIGI))
  if (!kullaniciId) return null
  const hamKiraci = basliklar.get(KIRACI_BASLIGI)?.trim()
  // Kiracı sınıfı yalnızca bilinen iki değerden biri olabilir; tanınmayan
  // her şey `sistem`e düşer (dar tarafta hata yapmak).
  const kiraci: KiraciSinifi = hamKiraci === 'kullanici' ? 'kullanici' : 'sistem'
  // Tutarlılık: 'sistem' kimliği asla 'kullanici' sınıfı taşıyamaz.
  if (kullaniciId === SISTEM_KIRACI && kiraci === 'kullanici') {
    return { kullaniciId: SISTEM_KIRACI, kiraci: 'sistem' }
  }
  return { kullaniciId, kiraci }
}

/**
 * Kimlikten dosya sistemi / Redis anahtarı için GÜVENLİ bir bileşen üretir.
 *
 * kimlikDogrula'dan geçmiş bir değer zaten [0-9a-f-] ya da 'sistem'dir, yani
 * yol ayırıcı veya `..` içeremez. Bu fonksiyon o güvenceyi AÇIKÇA yeniden
 * kurar ki, çağıran tarafta doğrulamanın atlanması sessiz bir açığa dönüşmesin.
 */
export function anahtarBileseni(kimlik: Kimlik): string {
  const d = kimlikDogrula(kimlik.kullaniciId)
  if (!d) throw new Error('kiraci: dogrulanmamis kimlik anahtar uretiminde kullanilamaz')
  return d
}
