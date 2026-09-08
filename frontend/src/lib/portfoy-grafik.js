/**
 * Portfoy performans grafigi — SAF GEOMETRI (Madde 30).
 *
 * EN KRITIK KURAL: OLCULEMEYEN NOKTADAN CIZGI GECMEZ
 * ==================================================
 * Bir gunun piyasa degeri olculemediyse cizgi o noktayi ATLAYARAK devam
 * EDEMEZ; kirilir ve bosluk gorunur. Atlayarak devam etmek, olculmemis bir
 * araligi olculmus gibi gostermek olurdu — bu depoda 232d1a0 ile kurulan
 * "olculemedi != sifir" ayriminin grafik katmanindaki karsiligi. (Sifir
 * yazmak da ayni sekilde yasak: pozisyon degersizlesmis gibi gorunurdu.)
 *
 * Maliyet cizgisi ile piyasa degeri cizgisi AYNI olcekte cizilir; iki ayri
 * y ekseni KULLANILMAZ (iki farkli olcekli eksen, gorsellestirmenin en sik
 * yapilan hatasidir ve iki seriyi keyfi olarak kesistirir).
 */

export const KENAR = { ust: 10, sag: 10, alt: 22, sol: 46 }

export function olcek(degerler, uzunluk, tersCevir = false) {
  const gecerli = degerler.filter((d) => typeof d === 'number' && Number.isFinite(d))
  if (!gecerli.length) return null
  let alt = Math.min(...gecerli)
  let ust = Math.max(...gecerli)
  if (alt === ust) { alt -= 1; ust += 1 }   // duz seride sifira bolme yok
  return (v) => {
    const oran = (v - alt) / (ust - alt)
    return tersCevir ? uzunluk - oran * uzunluk : oran * uzunluk
  }
}

/**
 * Noktalari, OLCULEMEYEN yerlerde KIRILAN parcalara boler.
 * Doner: [[{x,y}, ...], [{x,y}, ...]] — her dizi ayri bir cizgi parcasi.
 */
export function parcalar(noktalar, alan) {
  const { genislik, yukseklik } = alan
  const cizimG = genislik - KENAR.sol - KENAR.sag
  const cizimY = yukseklik - KENAR.ust - KENAR.alt
  const tumDegerler = noktalar.flatMap((n) => [n.maliyet, n.deger])
  const y = olcek(tumDegerler, cizimY, true)
  if (!y || noktalar.length === 0) return { maliyet: [], deger: [], y: null }

  const x = (i) => KENAR.sol + (noktalar.length === 1
    ? cizimG / 2
    : (i * cizimG) / (noktalar.length - 1))

  const bol = (secici) => {
    const cikti = []
    let parca = []
    noktalar.forEach((n, i) => {
      const v = secici(n)
      if (typeof v === 'number' && Number.isFinite(v)) {
        parca.push({ x: x(i), y: KENAR.ust + y(v), gun: n.gun, deger: v })
      } else if (parca.length) {
        cikti.push(parca); parca = []
      }
    })
    if (parca.length) cikti.push(parca)
    return cikti
  }
  return { maliyet: bol((n) => n.maliyet), deger: bol((n) => n.deger), y }
}

/** SVG polyline "points" dizgisi. */
export function yol(parca) {
  return parca.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
}

/** Y ekseni icin makul kademe degerleri. */
export function kademeler(degerler, adet = 4) {
  const gecerli = degerler.filter((d) => typeof d === 'number' && Number.isFinite(d))
  if (!gecerli.length) return []
  const alt = Math.min(...gecerli), ust = Math.max(...gecerli)
  if (alt === ust) return [alt]
  const adim = (ust - alt) / (adet - 1)
  return Array.from({ length: adet }, (_, i) => alt + i * adim)
}

/**
 * Eksen etiketi bicimi.
 *
 * ILK SURUMDE "10.2B" YAZIYORDU ve BELIRSIZDI: Turkce okuyan "bin", Ingilizce
 * okuyan "billion" anlayabilirdi. Portfoy buyuklukleri bu sistemde binler
 * mertebesinde oldugu icin kisaltmaya gerek yok; tr-TR binlik ayraciyla tam
 * sayi yazilir (10.202). Yalnizca milyon ustunde kisaltilir ve orada da
 * belirsiz olmayan " mn" eki kullanilir.
 */
export function paraKisa(v) {
  if (typeof v !== 'number' || !Number.isFinite(v)) return '—'
  if (Math.abs(v) >= 1_000_000) {
    return (v / 1_000_000).toLocaleString('tr-TR', { maximumFractionDigits: 1 }) + ' mn'
  }
  return Math.round(v).toLocaleString('tr-TR')
}
