// Grafik cizimlerinin kaliciligi - C3 / ADR-2 (localStorage, kullanici+sembol ad alanli).
//
// NEDEN depo disaridan enjekte edilir: modul localStorage'a DOGRUDAN baglanmaz.
// Boylece (a) node:test altinda DOM'suz, deterministik kosar; (b) gizli sekme /
// depolamasi kapali tarayici gibi erisim hatalari cagirana GORUNUR bicimde
// raporlanir, sessizce yutulmaz (ADR-2 "fail-loud").
import { gecerliCizim, type Cizim } from './cizim-model'

// Sema otoritesi cizim-model.ts'dir: burada IKINCI bir Cizim tipi tanimlansaydi
// iki taraf sessizce ayrisirdi (ornegin tip adi 'fib' <-> 'fibonacci') ve
// kaydedilen her cizim yuklemede "semaya uymuyor" diye atlanirdi.
export type { Cizim }

export interface Depo {
  getItem(anahtar: string): string | null
  setItem(anahtar: string, deger: string): void
  removeItem(anahtar: string): void
}

export interface KaydetSonucu {
  basarili: boolean
  hata?: string
  /**
   * Yazma, tarayici deposu KOTASI doldugu icin basarisiz oldu (Y9). Ayri bir
   * isaret: arayuz bu durumda teknik hata adini degil, kullanicinin ne
   * yapabilecegini soyleyen bir metin gosterir.
   */
  kotaDoldu?: true
}

export interface YuklemeSonucu {
  cizimler: Cizim[]
  uyari?: string
}

const ANAHTAR_ONEKI = 'alphawise:grafik:cizim:v1'
const SURUM = 1
const ANONIM_KIMLIK = 'anonim'

/**
 * NEDEN kacislama: kimlik ve sembol anahtara ham gomulurse ayrac enjeksiyonu
 * ad alanlarini cakistirir - ornegin kimlik "a" + sembol "B:C" ile kimlik "a:B" +
 * sembol "C" ayni anahtari uretirdi, yani bir kullanici digerinin kaydini okurdu.
 * encodeURIComponent ':' karakterini %3A yapar; alfanumerik kimliklere dokunmaz,
 * bu yuzden normal anahtar bicimi ADR-2'deki gibi okunabilir kalir.
 */
function parcaKacisla(parca: string): string {
  return encodeURIComponent(parca)
}

/**
 * Anahtar bicimi: alphawise:grafik:cizim:v1:<kullanici>:<SEMBOL>
 *
 * Kimlik bos/undefined ise 'anonim' kullanilir; bu AYRI bir ad alanidir -
 * oturum acmamis kullanicinin cizimleri hicbir gercek kullaniciya karismaz.
 *
 * Imza gorevde `string` olarak verilmisti; JS tarafindan gelen undefined/null
 * (ornegin oturum yokken user.id) de calisma aninda 'anonim'e dusmeli, bu yuzden
 * tip bilerek genisletildi - daralmadi, mevcut tum cagrilar gecerli kalir.
 */
export function anahtarUret(kullaniciKimligi: string | null | undefined, sembol: string): string {
  return adAlaniAnahtari(ANAHTAR_ONEKI, kullaniciKimligi, sembol)
}

/**
 * Kullanici+sembol ad alanli anahtar: `<onek>:<kullanici>:<SEMBOL>`.
 *
 * NEDEN DISA ACIK: gosterge kaliciligi (ADR-5) ayni ad alanlama desenini
 * kullanir. Kacislama ve normalizasyon kiraci izolasyonunun kendisidir;
 * ikinci bir kopyasi sessizce ayrisip bir turu sizintiya acik birakirdi.
 */
export function adAlaniAnahtari(
  onek: string,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
): string {
  const kimlik = typeof kullaniciKimligi === 'string' && kullaniciKimligi.trim() !== ''
    ? kullaniciKimligi.trim()
    : ANONIM_KIMLIK
  // toLocaleUpperCase DEGIL: Turkce yerelde 'i' -> 'İ' olur ve ayni sembol iki
  // farkli anahtar uretirdi. toUpperCase yerelden bagimsizdir (determinizm).
  const normalSembol = sembol.trim().toUpperCase()
  return `${onek}:${parcaKacisla(kimlik)}:${parcaKacisla(normalSembol)}`
}

function hataMetni(hata: unknown): string {
  return hata instanceof Error ? `${hata.name}: ${hata.message}` : String(hata)
}

/**
 * Hata bir depolama KOTASI hatasi mi? Tarayicilar farkli bicimler kullanir:
 * Chromium/WebKit `QuotaExceededError`, eski Firefox `NS_ERROR_DOM_QUOTA_REACHED`,
 * eski WebKit yalnizca `code === 22`. Ad eslesmesi Error/DOMException disi
 * degerlerde yapilmaz (duz bir metin kota hatasi degildir).
 */
export function kotaHatasiMi(hata: unknown): boolean {
  if (!(hata instanceof Error)) return false
  if (hata.name === 'QuotaExceededError' || hata.name === 'NS_ERROR_DOM_QUOTA_REACHED') return true
  return (hata as { code?: unknown }).code === 22
}

/** Yakalanan yazma hatasini KaydetSonucu'na cevirir; kota ayri isaretlenir. */
export function yazmaHatasi(hata: unknown): KaydetSonucu {
  const sonuc: KaydetSonucu = { basarili: false, hata: `kaydedilemedi: ${hataMetni(hata)}` }
  if (kotaHatasiMi(hata)) sonuc.kotaDoldu = true
  return sonuc
}

/**
 * JSON'dan gelen bilinmeyen bir degeri Cizim'e daraltir.
 *
 * Alan bazli dogrulama (surum, kimlik, nokta sayisi, sonlu sayi) TEKRARLANMAZ;
 * cizim-model.ts'deki gecerliCizim tek otoritedir. Burada yalnizca ona
 * guvenle dal verebilmek icin "nesne mi" on kontrolu yapilir.
 */
function cizimMi(deger: unknown): deger is Cizim {
  if (typeof deger !== 'object' || deger === null) return false
  return gecerliCizim(deger as Cizim)
}

/** Dizideki gecerli cizimleri ayiklar; atlananlarin SAYISI uyariya yazilir (sessiz kayip yok). */
function cizimleriAyikla(ham: unknown[], oncekiUyari?: string): YuklemeSonucu {
  const cizimler: Cizim[] = []
  let atlanan = 0
  for (const oge of ham) {
    if (cizimMi(oge)) cizimler.push(oge)
    else atlanan += 1
  }
  const uyarilar: string[] = []
  if (oncekiUyari !== undefined) uyarilar.push(oncekiUyari)
  if (atlanan > 0) uyarilar.push(`${atlanan} cizim semaya uymadigi icin atlandi`)
  return uyarilar.length > 0 ? { cizimler, uyari: uyarilar.join('; ') } : { cizimler }
}

/**
 * Cizimleri surumlu zarfla yazar. QuotaExceededError dahil TUM hatalar yakalanir
 * ve {basarili:false, hata} olarak doner - FIRLATMAZ, cunku cizim bellekte
 * durmaya devam eder ve arayuz "kaydedilemedi" uyarisini gosterir (ADR-2).
 */
export function kaydet(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
  cizimler: Cizim[],
): KaydetSonucu {
  const anahtar = anahtarUret(kullaniciKimligi, sembol)
  try {
    depo.setItem(anahtar, JSON.stringify({ v: SURUM, cizimler }))
    return { basarili: true }
  } catch (hata) {
    return yazmaHatasi(hata)
  }
}

/**
 * Kayitli cizimleri okur. YAN ETKISIZDIR: bozuk/eski kayitta bile depoya YAZMAZ.
 * NEDEN: yukle cizim yolundan cagrilir; orada bir yazma denemesi kendi kota
 * hatasini dogurabilir. "sifirlandi" = donen gorunum bostur; bozuk kaydin
 * uzerine bir sonraki kaydet yazar, kasitli temizlik icin sil() vardir.
 */
export function yukle(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
): YuklemeSonucu {
  const anahtar = anahtarUret(kullaniciKimligi, sembol)

  let ham: string | null
  try {
    ham = depo.getItem(anahtar)
  } catch (hata) {
    // Gizli sekme / depolama kapali: cokme yok, ama sessizlik de yok.
    return { cizimler: [], uyari: `depo okunamadi: ${hataMetni(hata)}` }
  }
  if (ham === null || ham === undefined) return { cizimler: [] }

  let cozulen: unknown
  try {
    cozulen = JSON.parse(ham)
  } catch {
    return { cizimler: [], uyari: 'bozuk kayit sifirlandi' }
  }

  // v0 = zarftan onceki bicim: duz cizim dizisi. Guvenli goc DENENIR.
  if (Array.isArray(cozulen)) return cizimleriAyikla(cozulen, 'eski surum (v0) goc edildi')

  if (typeof cozulen !== 'object' || cozulen === null) {
    return { cizimler: [], uyari: 'bozuk kayit sifirlandi' }
  }

  const zarf = cozulen as Record<string, unknown>
  if (zarf.v !== SURUM) {
    // Goc edilemeyen surum (ileri surum ya da taninmayan deger): sifirla + uyar.
    return { cizimler: [], uyari: `bilinmeyen surum (v=${String(zarf.v)}) sifirlandi` }
  }
  if (!Array.isArray(zarf.cizimler)) return { cizimler: [], uyari: 'bozuk kayit sifirlandi' }

  return cizimleriAyikla(zarf.cizimler)
}

/** Sembolun kaydini siler. kaydet ile ayni sozlesme: hata firlatmaz, raporlar. */
export function sil(
  depo: Depo,
  kullaniciKimligi: string | null | undefined,
  sembol: string,
): KaydetSonucu {
  try {
    depo.removeItem(anahtarUret(kullaniciKimligi, sembol))
    return { basarili: true }
  } catch (hata) {
    return { basarili: false, hata: `silinemedi: ${hataMetni(hata)}` }
  }
}
