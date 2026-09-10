/**
 * Arama akisi — bagimsiz istekler AYNI ANDA baslar.
 *
 * NEDEN VAR (olculen kusur, 10.09.2026)
 * =====================================
 * dashboard/page.tsx icindeki handleSearch su siralamayi kuruyordu:
 *
 *     const resp = await fetch('/api/maa/narrative-verified/...')  // YAVAS
 *     ...
 *     fetch('/api/maa/memory/...')        // ancak buradan sonra basliyor
 *     ...
 *     fetch('/api/godmode/...')           // ve bu, await bittikten SONRA
 *
 * narrative-verified bir LLM cagrisidir ve saniyeler surer. God Mode ise
 * ondan TAMAMEN BAGIMSIZDIR — kodun kendi yorumu da bunu soyluyor
 * ("MAA sonucundan bagimsiz, ayri bir bolumde gosterilir"). Buna ragmen
 * God Mode istegi, MAA yaniti gelene kadar hic BASLAMIYORDU. Kullanici
 * iki bekleme suresini ust uste yasiyordu.
 *
 * Bu modul akisi tek yerde toplar: uc istek de cagrildigi anda baslar,
 * sonuclar geldikce ayri ayri islenir.
 *
 * NEDEN AYRI DOSYA
 * ================
 * page.tsx bir React bileseni ve bu depoda dogrudan test edilmiyor.
 * Siralama davranisini kilitlemek icin akis buraya cikarildi; testler
 * isteklerin GERCEKTEN es zamanli basladigini dogruluyor (bkz.
 * frontend/tests/arama-akisi.test.mjs).
 */

/**
 * Uc istegi de ayni anda baslatir ve promise'leri dondurur.
 *
 * @param {string} ticker  aranan sembol
 * @param {(url: string) => Promise<any>} getir  istek yapan fonksiyon
 * @returns {{maa: Promise, hafiza: Promise, godmode: Promise}}
 */
export function aramaAkisiBaslat(ticker, getir) {
  const t = String(ticker || '').trim().toUpperCase()
  if (!t) throw new Error('ticker bos olamaz')
  if (typeof getir !== 'function') throw new Error('getir bir fonksiyon olmali')

  // UCU DE BURADA, AYNI ANDA baslar. Aralarina await koymak, bu modulun
  // var olma nedenini ortadan kaldirir.
  const kod = encodeURIComponent(t)
  return {
    maa: getir(`/api/maa/narrative-verified/${kod}`),
    hafiza: getir(`/api/maa/memory/${kod}`),
    godmode: getir(`/api/godmode/${kod}`),
  }
}

/** Aranan sembolun temizlenmis hali (page.tsx ile ayni kural). */
export function sembolNormalize(ticker) {
  return String(ticker || '').trim().toUpperCase()
}
