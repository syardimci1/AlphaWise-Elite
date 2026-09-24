// Gosterge seciminin kaliciligi - ADR-5 / contracts/grafik/kalicilik_sozlesmesi.md.
//
// Cizim kaliciligiyla (cizim-kalicilik.ts, ADR-2) AYNI sozlesme: depo disaridan
// enjekte edilir, hata firlatilmaz raporlanir, okuma yan etkisizdir. Ad alani
// kodu oradan gelir; burada kopyalanmaz.
import { adAlaniAnahtari, yazmaHatasi, type Depo, type KaydetSonucu } from './cizim-kalicilik'
import { gostergeKimlikMi, tumGostergeKimlikleri, type GostergeKimlik } from './gosterge-tanim'

export interface GostergeYuklemeSonucu {
  gostergeler: GostergeKimlik[]
  uyari?: string
}

const ANAHTAR_ONEKI = 'alphawise:grafik:gosterge:v1'
const SURUM = 1

/** Anahtar bicimi: alphawise:grafik:gosterge:v1:<kullanici>:<SEMBOL> */
export function gostergeAnahtari(kullaniciKimligi: string | null | undefined, sembol: string): string {
  return adAlaniAnahtari(ANAHTAR_ONEKI, kullaniciKimligi, sembol)
}

function hataMetni(hata: unknown): string {
  return hata instanceof Error ? `${hata.name}: ${hata.message}` : String(hata)
}

/**
 * Secimi surumlu zarfla yazar. `guncelleme_utc` DISARIDAN gelir (saflik:
 * modul Date.now() cagirmaz, ayni girdi ayni ciktiyi verir).
 */
export function gostergeleriKaydet(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
  gostergeler: readonly GostergeKimlik[],
  guncelleme_utc: number,
): KaydetSonucu {
  const anahtar = gostergeAnahtari(kullaniciKimligi, sembol)
  try {
    depo.setItem(anahtar, JSON.stringify({ v: SURUM, gostergeler, guncelleme_utc }))
    return { basarili: true }
  } catch (hata) {
    return yazmaHatasi(hata)
  }
}

const BOZUK = 'bozuk kayit sifirlandi'

/**
 * Bilinen kimlikleri kanonik siraya dizer; tekrarlar tek kalir. Taninmayan
 * ogelerin SAYISI uyariya yazilir (sessiz kayip yok) - ornegin eski bir
 * surumde var olup artik tanimlanmayan bir gosterge.
 */
function ayikla(ham: unknown[], oncekiUyari?: string): GostergeYuklemeSonucu {
  const kume = new Set<GostergeKimlik>()
  let atlanan = 0
  for (const oge of ham) {
    if (typeof oge === 'string' && gostergeKimlikMi(oge)) kume.add(oge)
    else atlanan += 1
  }
  const gostergeler = tumGostergeKimlikleri().filter((kimlik) => kume.has(kimlik))
  const uyarilar: string[] = []
  if (oncekiUyari !== undefined) uyarilar.push(oncekiUyari)
  if (atlanan > 0) uyarilar.push(`${atlanan} gosterge taninmadigi icin atlandi`)
  return uyarilar.length > 0 ? { gostergeler, uyari: uyarilar.join('; ') } : { gostergeler }
}

/**
 * Kayitli secimi okur. YAN ETKISIZDIR: bozuk/eski kayitta bile depoya YAZMAZ
 * (cizim-kalicilik.yukle ile ayni gerekce). Hicbir yol firlatmaz; kayip
 * olan her yol `uyari` tasir (C4).
 */
export function gostergeleriYukle(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
): GostergeYuklemeSonucu {
  let ham: string | null
  try {
    ham = depo.getItem(gostergeAnahtari(kullaniciKimligi, sembol))
  } catch (hata) {
    return { gostergeler: [], uyari: `depo okunamadi: ${hataMetni(hata)}` }
  }
  if (ham === null) return { gostergeler: [] }

  let cozulen: unknown
  try {
    cozulen = JSON.parse(ham)
  } catch {
    return { gostergeler: [], uyari: BOZUK }
  }

  // v0 = zarftan onceki bicim: duz kimlik dizisi. Guvenli goc DENENIR.
  if (Array.isArray(cozulen)) return ayikla(cozulen, 'eski surum (v0) goc edildi')
  if (typeof cozulen !== 'object' || cozulen === null) return { gostergeler: [], uyari: BOZUK }

  const zarf = cozulen as Record<string, unknown>
  if (zarf.v !== SURUM) {
    return { gostergeler: [], uyari: `bilinmeyen surum (v=${String(zarf.v)}) sifirlandi` }
  }
  if (!Array.isArray(zarf.gostergeler)) return { gostergeler: [], uyari: BOZUK }
  return ayikla(zarf.gostergeler)
}

/** Sembolun gosterge kaydini siler. Hata firlatmaz, raporlar. */
export function gostergeleriSil(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
): KaydetSonucu {
  try {
    depo.removeItem(gostergeAnahtari(kullaniciKimligi, sembol))
    return { basarili: true }
  } catch (hata) {
    return { basarili: false, hata: `silinemedi: ${hataMetni(hata)}` }
  }
}
