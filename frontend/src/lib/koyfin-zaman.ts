// Koyfin olay katmani - Zaman Sozlesmesi (contracts/C4_zaman_sozlesmesi.md).
//
// TEK KURAL: ic temsilin TAMAMI UTC ms epoch'tur. Yerel saate donusum
// YALNIZCA bu dosyada, gorunum anida yapilir. Baska hicbir dosya
// Date(...) veya string tarih ayristirmasi YAPMAMALIDIR (C1/C2 semasini
// dolduran normalize fonksiyonlari da bu dosyadaki yardimcilari kullanir).

/**
 * "YYYY-MM-DD" bicimindeki gun-hassasiyetli bir tarihi UTC gece yarisi
 * epoch ms'e cevirir. Date.UTC kullanir - tarayicinin yerel saat dilimini
 * ASLA devreye sokmaz (bkz. C4: sinir gunlerinde bir gun kayma riski).
 */
export function gunStringindenUtcMs(gun: string): number {
  const [yil, ay, g] = gun.split('-').map(Number)
  return Date.UTC(yil, ay - 1, g)
}

/** UTC ms epoch'u lightweight-charts'in "business day" string bicimine geri cevirir. */
export function utcMsToIsGunuString(ts_utc: number): string {
  const d = new Date(ts_utc)
  const yil = d.getUTCFullYear()
  const ay = String(d.getUTCMonth() + 1).padStart(2, '0')
  const gun = String(d.getUTCDate()).padStart(2, '0')
  return `${yil}-${ay}-${gun}`
}

/** Kullanicinin tarayici yerel saatinde goruntulenecek etiket. */
export function utcMsToYerelEtiket(ts_utc: number, locale = 'tr-TR'): string {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(ts_utc))
}
