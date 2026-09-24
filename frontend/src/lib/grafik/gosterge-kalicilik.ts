// Gosterge seciminin kaliciligi - ADR-5 / contracts/grafik/kalicilik_sozlesmesi.md.
//
// Cizim kaliciligiyla (cizim-kalicilik.ts, ADR-2) AYNI sozlesme: depo disaridan
// enjekte edilir, hata firlatilmaz raporlanir, okuma yan etkisizdir. Ad alani
// kodu oradan gelir; burada kopyalanmaz.
import { adAlaniAnahtari, type Depo, type KaydetSonucu } from './cizim-kalicilik'
import { tumGostergeKimlikleri, type GostergeKimlik } from './gosterge-tanim'

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
    return { basarili: false, hata: `kaydedilemedi: ${hataMetni(hata)}` }
  }
}

/** Bilinen kimlikleri kanonik siraya dizer; tekrarlar tek kalir. */
function kanonik(ham: unknown[]): GostergeKimlik[] {
  const kume = new Set<unknown>(ham)
  return tumGostergeKimlikleri().filter((kimlik) => kume.has(kimlik))
}

/** Kayitli secimi okur. YAN ETKISIZDIR: bozuk kayitta bile depoya yazmaz. */
export function gostergeleriYukle(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
): GostergeYuklemeSonucu {
  const ham = depo.getItem(gostergeAnahtari(kullaniciKimligi, sembol))
  if (ham === null) return { gostergeler: [] }
  const zarf = JSON.parse(ham) as { v: unknown; gostergeler: unknown[] }
  if (zarf.v !== SURUM) return { gostergeler: [] }
  return { gostergeler: kanonik(zarf.gostergeler) }
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
