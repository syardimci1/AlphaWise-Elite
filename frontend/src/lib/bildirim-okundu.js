/**
 * Bildirim merkezi — OKUNDU/OKUNMADI kalicilik mantigi (Y10 boslugu, saf).
 *
 * NEDEN AYRI MODUL (bildirim-ozet.js'e DOKUNULMADI)
 * ==================================================
 * bildirim-ozet.js zaten 18 testle kanitli, calisan bir modul. rozetSayisi()
 * imzasini degistirmek yerine, okundu/okunmadi mantigi tamamen ayri, saf ve
 * test edilebilir bu dosyada yasiyor (Y5: tek mantiksal degisiklik/commit,
 * atomik geri alinabilirlik).
 *
 * AD ALANI DESENI: frontend/src/lib/grafik/gosterge-kalicilik.ts ile TUTARLI
 * (kullanici bazli localStorage anahtari). KALICILIK_SONUC.md/WATCHLIST_
 * SONUC.md depoda bulunamadi (FAZ 0); bu, depodaki TEK dogrulanmis emsal.
 */

export const ANAHTAR_ONEKI = 'alphawise:bildirim:okundu:v1'
export const AZAMI_OKUNAN = 500 // /bildirimler zaten azami=40 dondugu icin pratikte hic dolmaz

/**
 * Bildirimin kararli kimligi. Ayni ucluyu (kaynak,zaman,mesaj) toplayici.py
 * de tekillestirme icin kullaniyor (bkz. toplayici.py:tekille) - burada da
 * ayni anahtar kullanilarak sunucu/istemci ayrisması onleniyor.
 *
 * Kripto-guvenli DEGIL (FNV-1a benzeri, senkron) - kimlik amacli, guvenlik
 * amacli degil; senkron calismasi gerekiyor (React state guncellemesi
 * sirasinda await edilemez) ve yeni bagimlilik eklenmiyor (Y2).
 */
export function bildirimIdUret(b) {
  const girdi = `${b.kaynak ?? ''}|${b.zaman ?? ''}|${b.mesaj ?? ''}`
  let h = 0x811c9dc5
  for (let i = 0; i < girdi.length; i++) {
    h ^= girdi.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return (h >>> 0).toString(16).padStart(8, '0')
}

export function okunanAnahtari(kullaniciId) {
  return `${ANAHTAR_ONEKI}:${kullaniciId}`
}

/** Depodan okunan id kumesini doner. Erisim hatasinda (private mode vb.)
 * BOS Set doner, ASLA atmaz - okundu/okunmadi ozelligi opsiyoneldir,
 * bildirim listesini cokertmemeli (fail-safe, Y11 ruhu). */
export function okunanlariOku(depo, kullaniciId) {
  try {
    const ham = depo.getItem(okunanAnahtari(kullaniciId))
    if (!ham) return new Set()
    const dizi = JSON.parse(ham)
    return Array.isArray(dizi) ? new Set(dizi) : new Set()
  } catch {
    return new Set()
  }
}

/** Bir bildirimi okundu isaretler. AZAMI_OKUNAN asilirsa EN ESKI id
 * dusurulur (sinirsiz buyume yok). Depo hatasinda sessizce yutulur. */
export function okunduIsaretle(depo, kullaniciId, id) {
  try {
    const mevcutSet = okunanlariOku(depo, kullaniciId)
    mevcutSet.delete(id) // sona tasimak icin once sil (insertion-order korunur)
    mevcutSet.add(id)
    let dizi = [...mevcutSet]
    if (dizi.length > AZAMI_OKUNAN) dizi = dizi.slice(dizi.length - AZAMI_OKUNAN)
    depo.setItem(okunanAnahtari(kullaniciId), JSON.stringify(dizi))
  } catch {
    // kota asimi / gizli sekme: kalicilik basarisiz oldu ama uygulama cokmez.
  }
}

/** Okunmamis kritik+alarm sayisi. rozetSayisi()'nin (bildirim-ozet.js) TOPLAM
 * dondurmesinden farkli olarak, kullanici panoyu actiginda gercekten SIFIRA
 * doner - eski davranista rozet asla sifirlanmiyordu. */
export function okunmamisSayi(bildirimler, okunanIdSeti) {
  return bildirimler.filter(
    (b) => (b.duzey === 'kritik' || b.duzey === 'alarm') && !okunanIdSeti.has(bildirimIdUret(b))
  ).length
}
