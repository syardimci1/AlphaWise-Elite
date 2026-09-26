// Karsilastirma seciminin kaliciligi - contracts/grafik/karsilastirma_modu.md C5.
//
// ADR-5'in UCUNCU turu: cizim (ADR-2) ve gosterge (ADR-5) ile AYNI sozlesme.
// Depo disaridan enjekte edilir, hata firlatilmaz raporlanir, okuma yan
// etkisizdir, ad alani kodu cizim-kalicilik.adAlaniAnahtari'ndan gelir -
// burada kopyalanmaz (Y8: yeni mekanizma icat edilmez).
//
// Ad alanindaki sembol ANA semboldur: "AAPL grubunun karsilastirmalari" AAPL'ye aittir.
import { adAlaniAnahtari, yazmaHatasi, type Depo, type KaydetSonucu } from './cizim-kalicilik'
import {
  AZAMI_GRUP,
  bosSecim,
  sembolNormalize,
  type EkSembol,
  type KarsilastirmaSecimi,
} from './karsilastirma'

export interface KarsilastirmaYuklemeSonucu {
  secim: KarsilastirmaSecimi
  uyari?: string
}

const ANAHTAR_ONEKI = 'alphawise:grafik:karsilastirma:v1'
const SURUM = 1
const BOZUK = 'bozuk kayit sifirlandi'

/** Anahtar bicimi: alphawise:grafik:karsilastirma:v1:<kullanici>:<ANA_SEMBOL> */
export function karsilastirmaAnahtari(kullaniciKimligi: string | null | undefined, anaSembol: string): string {
  return adAlaniAnahtari(ANAHTAR_ONEKI, kullaniciKimligi, anaSembol)
}

function hataMetni(hata: unknown): string {
  return hata instanceof Error ? `${hata.name}: ${hata.message}` : String(hata)
}

/** Secimi surumlu zarfla yazar. `guncelleme_utc` DISARIDAN gelir (saflik). */
export function karsilastirmaKaydet(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  anaSembol: string,
  secim: KarsilastirmaSecimi,
  guncelleme_utc: number,
): KaydetSonucu {
  try {
    depo.setItem(
      karsilastirmaAnahtari(kullaniciKimligi, anaSembol),
      JSON.stringify({ v: SURUM, mod: secim.mod, semboller: secim.semboller, guncelleme_utc }),
    )
    return { basarili: true }
  } catch (hata) {
    return yazmaHatasi(hata)
  }
}

/**
 * Sembol listesini ayiklar: gecersiz bicim, yinelenen, ana sembole esit,
 * tanimsiz ya da cakisan yuva, ve 2'yi asan ogeler atlanir. SAYISI uyariya
 * yazilir (C4 deseni: sessiz kayip yok). Ilk gelen kalir.
 */
function ayikla(ham: unknown[], anaSembol: string): { semboller: EkSembol[]; atlanan: number } {
  const ana = anaSembol.trim().toUpperCase()
  const semboller: EkSembol[] = []
  let atlanan = 0
  for (const oge of ham) {
    const kayit = typeof oge === 'object' && oge !== null ? (oge as Record<string, unknown>) : null
    const sembol = kayit !== null && typeof kayit.sembol === 'string' ? sembolNormalize(kayit.sembol) : null
    const yuva = kayit?.yuva
    const gecerli =
      sembol !== null &&
      sembol !== ana &&
      (yuva === 1 || yuva === 2) &&
      !semboller.some((s) => s.sembol === sembol || s.yuva === yuva) &&
      semboller.length + 1 < AZAMI_GRUP
    if (gecerli) semboller.push({ sembol: sembol as string, yuva: yuva as 1 | 2 })
    else atlanan += 1
  }
  return { semboller, atlanan }
}

/**
 * Kayitli secimi okur. YAN ETKISIZDIR (bozuk kayitta bile depoya yazmaz).
 * Hicbir yol firlatmaz; kayip olan her yol `uyari` tasir.
 */
export function karsilastirmaYukle(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  anaSembol: string,
): KarsilastirmaYuklemeSonucu {
  let ham: string | null
  try {
    ham = depo.getItem(karsilastirmaAnahtari(kullaniciKimligi, anaSembol))
  } catch (hata) {
    return { secim: bosSecim(), uyari: `depo okunamadi: ${hataMetni(hata)}` }
  }
  if (ham === null) return { secim: bosSecim() }

  let cozulen: unknown
  try {
    cozulen = JSON.parse(ham)
  } catch {
    return { secim: bosSecim(), uyari: BOZUK }
  }
  if (typeof cozulen !== 'object' || cozulen === null || Array.isArray(cozulen)) {
    return { secim: bosSecim(), uyari: BOZUK }
  }
  const zarf = cozulen as Record<string, unknown>
  if (zarf.v !== SURUM) return { secim: bosSecim(), uyari: `bilinmeyen surum (v=${String(zarf.v)}) sifirlandi` }
  if ((zarf.mod !== 'tek' && zarf.mod !== 'karsilastirma') || !Array.isArray(zarf.semboller)) {
    return { secim: bosSecim(), uyari: BOZUK }
  }
  const { semboller, atlanan } = ayikla(zarf.semboller, anaSembol)
  const secim: KarsilastirmaSecimi = { mod: zarf.mod, semboller }
  return atlanan > 0 ? { secim, uyari: `${atlanan} karsilastirma sembolu gecersiz oldugu icin atlandi` } : { secim }
}

/** Ana sembolun karsilastirma kaydini siler. Hata firlatmaz, raporlar. */
export function karsilastirmaSil(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  anaSembol: string,
): KaydetSonucu {
  try {
    depo.removeItem(karsilastirmaAnahtari(kullaniciKimligi, anaSembol))
    return { basarili: true }
  } catch (hata) {
    return { basarili: false, hata: `silinemedi: ${hataMetni(hata)}` }
  }
}
