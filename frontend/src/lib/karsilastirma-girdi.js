/**
 * Cok sembollu karsilastirma ekraninin GIRDI mantigi (Madde 29).
 *
 * NEDEN SAF VE AYRI
 * =================
 * Kullanicinin yazdigi serbest metni sembol listesine cevirmek gorunurde
 * onemsiz ama uc sessiz hata uretmeye musait: (1) gecersiz sembolu sessizce
 * atmak, (2) yinelenenleri iki kez sorgulamak, (3) sinirsiz sembol kabul edip
 * sunucuyu ve hiz sinirini zorlamak. Ucu de kullaniciya HICBIR SEY
 * soylemeden olur. Bu yuzden mantik burada, testli ve saf.
 *
 * OLCULEN SINIR
 * =============
 * Tek sembollu dashboard acilisi ZATEN 11 es zamanli istek harciyor ve
 * middleware'deki 'sinyal' sinifinin anlik patlama tavani 35. Tarayicidan
 * N sembol x M servis cagirmak ekrani KENDI KENDINE 429'a dusururdu. Bu
 * yuzden tarayici TEK istek yapar, fan-out sunucuda olur; buradaki tavan da
 * sunucu tarafi fan-out'u ve tablonun okunabilirligini sinirlar.
 */

// servis-proxy.ts ile AYNI desen. Kopya olmasi bilincli: bu modul saf JS ve
// bagimlilik almadan node ile kosuyor. Ikisinin ayrismasini test kilitler.
export const SEMBOL_DESENI = /^[A-Z0-9]+(?:[.-][A-Z0-9]+)*$/
export const SEMBOL_AZAMI_UZUNLUK = 10
export const AZAMI_SEMBOL = 8

/**
 * Serbest metni sembol listesine cevirir.
 * Doner: { semboller, reddedilen, yinelenen, kesilen }
 * Hicbir sey SESSIZCE atilmaz; her ayiklama ayri alanda raporlanir.
 */
export function sembolleriAyristir(ham, azami = AZAMI_SEMBOL) {
  const parcalar = String(ham || '')
    .split(/[\s,;]+/)
    .map((p) => p.trim().toUpperCase())
    .filter(Boolean)

  const semboller = []
  const reddedilen = []
  const yinelenen = []
  for (const p of parcalar) {
    if (p.length > SEMBOL_AZAMI_UZUNLUK || !SEMBOL_DESENI.test(p)) {
      if (!reddedilen.includes(p)) reddedilen.push(p)
      continue
    }
    if (semboller.includes(p)) {
      if (!yinelenen.includes(p)) yinelenen.push(p)
      continue
    }
    semboller.push(p)
  }
  const kesilen = semboller.slice(azami)
  return { semboller: semboller.slice(0, azami), reddedilen, yinelenen, kesilen }
}

/** Kullaniciya gosterilecek uyari metinleri; bos dizi = uyari yok. */
export function girdiUyarilari(sonuc, azami = AZAMI_SEMBOL) {
  const u = []
  if (sonuc.reddedilen.length) {
    u.push(`Geçersiz sembol yok sayıldı: ${sonuc.reddedilen.join(', ')}`)
  }
  if (sonuc.yinelenen.length) {
    u.push(`Yinelenen sembol bir kez alındı: ${sonuc.yinelenen.join(', ')}`)
  }
  if (sonuc.kesilen.length) {
    u.push(`En fazla ${azami} sembol karşılaştırılır; şunlar alınmadı: ` +
           `${sonuc.kesilen.join(', ')}`)
  }
  return u
}

/**
 * Bir hucrenin gosterim degeri. OLCULEMEDI ile SIFIR ayrimi burada da korunur:
 * null/undefined -> '—' (olculemedi), 0 -> '0' (gercek olcum).
 */
export function hucre(deger, basamak = 2) {
  if (deger === null || deger === undefined) return '—'
  if (typeof deger === 'number') {
    if (!Number.isFinite(deger)) return '—'
    return deger.toLocaleString('tr-TR', { maximumFractionDigits: basamak })
  }
  return String(deger)
}

/** Bir sembol satirinda kac alan olculebildi. */
export function olculenAlanSayisi(satir, alanlar) {
  return alanlar.filter((a) => {
    const v = satir[a]
    return v !== null && v !== undefined && !(typeof v === 'number' && !Number.isFinite(v))
  }).length
}
