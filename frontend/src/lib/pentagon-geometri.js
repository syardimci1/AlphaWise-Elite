/**
 * Bes eksenli skor gorseli — SAF GEOMETRI.
 *
 * NEDEN AYRI VE SAF BIR MODUL
 * ===========================
 * Frontend'de hicbir test altyapisi yok (jest/vitest/playwright sifir).
 * Gorselin en kritik kurali ise gozle bakarak dogrulanamayacak kadar
 * onemli: OLCULEMEYEN BIR EKSEN SIFIR UZUNLUKTA CIZILEMEZ. Bu kurali
 * React bilesenine gomsek, testi olmayan bir yerde yasardi. Bu yuzden
 * tum karar mantigi bagimlilik gerektirmeyen saf fonksiyonlara alindi;
 * duz `node` ile kosan gercek testleri var (pentagon-geometri.test.mjs).
 *
 * TEMEL SOZLESME
 * ==============
 * puan === null  -> tepe === null  (koseyi CIZME)
 * puan === 0     -> tepe MERKEZDE  (olculdu ve sifir; gecerli bir sonuc)
 * Ikisi ayni sekilde cizilirse, depoda 232d1a0 ile kapatilan
 * "olculemedi = notr" hatasi goruntu katmaninda geri gelir.
 */

export const OLCULDU = 'olculdu'
export const OLCULEMEDI = 'olculemedi'
export const UYGULANAMAZ = 'uygulanamaz'

/** Poligon cizmek icin gereken en az olculmus eksen sayisi. */
export const ASGARI_POLIGON_KOSESI = 3

/**
 * Kutupsal -> kartezyen. Ilk eksen TAM TEPEDE (-90 derece) baslar ve
 * saat yonunde ilerler; bu, okuyucunun "ilk eksen en ustte" beklentisini
 * karsilar.
 * @param {{x:number,y:number}} merkez
 * @param {number} yaricap
 * @param {number} indeks
 * @param {number} toplam
 */
export function kutupsal(merkez, yaricap, indeks, toplam) {
  const aci = -Math.PI / 2 + (2 * Math.PI * indeks) / toplam
  return {
    x: merkez.x + yaricap * Math.cos(aci),
    y: merkez.y + yaricap * Math.sin(aci),
  }
}

/**
 * Her eksen icin dis uc (etiket/izgara) ve varsa deger kosesi.
 * @param {Array<{anahtar:string,ad:string,puan:number|null,durum:string}>} eksenler
 */
export function eksenNoktalari(eksenler, merkez, yaricap) {
  const n = eksenler.length
  return eksenler.map((e, i) => {
    // SOZLESME: puan null ise KOSE YOK. `e.puan || 0` gibi bir kisayol
    // burada tam olarak yasak olan seyi yapardi (null -> 0).
    const olculdu = typeof e.puan === 'number' && Number.isFinite(e.puan)
    const oran = olculdu ? Math.max(0, Math.min(100, e.puan)) / 100 : null
    return {
      anahtar: e.anahtar,
      ad: e.ad,
      durum: e.durum,
      puan: olculdu ? e.puan : null,
      indeks: i,
      uc: kutupsal(merkez, yaricap, i, n),
      tepe: olculdu ? kutupsal(merkez, yaricap * oran, i, n) : null,
    }
  })
}

/**
 * Olculmus koseleri birlestiren kenarlar.
 *
 * Bir kenar, arada OLCULEMEYEN bir eksenin uzerinden atliyorsa
 * `atlamaVar: true` isaretlenir; bilesen bu kenarlari KESIKLI cizer.
 * Duz cizilseydi, okuyucu atlanan eksende de bir deger varmis gibi
 * yorumlardi.
 *
 * Ucten az kose varsa poligon HIC cizilmez: iki nokta bir alan
 * tanimlamaz ve "sekil" izlenimi yaniltici olurdu.
 */
export function poligonKenarlari(noktalar) {
  const olculen = noktalar.filter((p) => p.tepe !== null)
  if (olculen.length < ASGARI_POLIGON_KOSESI) return []
  const n = noktalar.length
  const kenarlar = []
  for (let k = 0; k < olculen.length; k++) {
    const a = olculen[k]
    const b = olculen[(k + 1) % olculen.length]
    // a'dan b'ye saat yonunde giderken kac eksen atlandi?
    let adim = (b.indeks - a.indeks + n) % n
    if (adim === 0) adim = n
    kenarlar.push({ a: a.tepe, b: b.tepe, atlamaVar: adim > 1,
                    aIndeks: a.indeks, bIndeks: b.indeks })
  }
  return kenarlar
}

/** Izgara halkalari (0-100 arasi kademeler). */
export function halkaYaricaplari(yaricap, kademeler = [25, 50, 75, 100]) {
  return kademeler.map((k) => ({ kademe: k, yaricap: (yaricap * k) / 100 }))
}

/** Bir halkanin cokgen kose dizisi (SVG points dizgisi). */
export function halkaNoktalari(merkez, yaricap, kenarSayisi) {
  const p = []
  for (let i = 0; i < kenarSayisi; i++) {
    const n = kutupsal(merkez, yaricap, i, kenarSayisi)
    p.push(`${n.x.toFixed(2)},${n.y.toFixed(2)}`)
  }
  return p.join(' ')
}

/** Etiket, dis ucun biraz disina konur. */
export function etiketKonumu(merkez, yaricap, indeks, toplam, pay = 26) {
  const n = kutupsal(merkez, yaricap + pay, indeks, toplam)
  const aci = -Math.PI / 2 + (2 * Math.PI * indeks) / toplam
  const cos = Math.cos(aci)
  // Tepe ve dipteki etiketler ortalanir; yanlardakiler ice bakar.
  const hiza = Math.abs(cos) < 0.2 ? 'middle' : cos > 0 ? 'start' : 'end'
  return { x: n.x, y: n.y, hiza }
}

/**
 * Eksenin ekranda yazacagi deger metni. Olculemeyen eksen icin ASLA
 * sayi dondurmez.
 */
export function durumMetni(eksen) {
  if (typeof eksen.puan === 'number' && Number.isFinite(eksen.puan)) {
    return String(Math.round(eksen.puan))
  }
  if (eksen.durum === UYGULANAMAZ) return 'uygulanamaz'
  return 'veri yok'
}

/**
 * Genel puan metni. null ise sayi UYDURULMAZ.
 */
export function genelPuanMetni(genelPuan) {
  return typeof genelPuan === 'number' && Number.isFinite(genelPuan)
    ? String(Math.round(genelPuan))
    : '—'
}

/**
 * Ozet satiri: kac eksen olculdu.
 */
export function kapsamMetni(eksenler, asgari) {
  const olculen = eksenler.filter(
    (e) => typeof e.puan === 'number' && Number.isFinite(e.puan)
  ).length
  const yeterli = olculen >= asgari
  return {
    olculen,
    toplam: eksenler.length,
    yeterli,
    metin: `${olculen}/${eksenler.length} eksen ölçüldü`,
  }
}

/**
 * Besgen uzerindeki eksen etiketi. Tam ad satirlarda zaten yaziyor; grafikte
 * uzun ad yan taraflarda kart kenarindan TASIYORDU (390px genislikte
 * olculdu). Kisa ad yalnizca grafikte kullanilir, veri kaybi olmaz.
 */
export function kisaAd(ad, esik = 10) {
  const t = String(ad || '')
  if (t.length <= esik) return t
  return t.split(' ')[0]
}
