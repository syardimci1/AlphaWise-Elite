// Koyfin olay katmani - Marker Semasi (contracts/C2_marker_semasi.md).
//
// KoyfinOlay[] -> lightweight-charts'in createSeriesMarkers() bekledigi
// bicime cevirir. Renk/ikon tablosu C2'de belgelenmis (VARSAYIM V-006).
import type { KoyfinOlay, KoyfinOlayTipi } from './koyfin-olaylar'
import { utcMsToIsGunuString } from './koyfin-zaman'

const RENK: Record<KoyfinOlayTipi, string> = {
  CONGRESS: '#e63946',
  INSIDER: '#f4a261',
  '13F': '#457b9d',
  DARK_POOL: '#6a4c93',
}

type SeriesMarkerSekli = 'arrowUp' | 'arrowDown' | 'circle' | 'square'
type SeriesMarkerKonumu = 'aboveBar' | 'belowBar'

export interface KoyfinLwcMarker {
  time: string // lightweight-charts business-day string (bkz. C4)
  position: SeriesMarkerKonumu
  shape: SeriesMarkerSekli
  color: string
  text: string
  id: string // event_id ile ayni (tooltip lookup icin)
}

function yonSekliVeKonumu(olay: KoyfinOlay): { shape: SeriesMarkerSekli; position: SeriesMarkerKonumu } {
  if (olay.tip === 'CONGRESS') {
    const tur = String(olay.ham_veri_ref.transaction_type || '').toLowerCase()
    return tur.includes('sale')
      ? { shape: 'arrowDown', position: 'aboveBar' }
      : { shape: 'arrowUp', position: 'belowBar' }
  }
  if (olay.tip === 'INSIDER') {
    const yon = olay.ham_veri_ref.acik_piyasa_yonu as string | null
    if (yon === 'satis') return { shape: 'arrowDown', position: 'aboveBar' }
    if (yon === 'alis') return { shape: 'arrowUp', position: 'belowBar' }
    return { shape: 'circle', position: 'aboveBar' } // hibe/odul - yon tasimaz
  }
  if (olay.tip === '13F') return { shape: 'circle', position: 'aboveBar' }
  return { shape: 'square', position: 'aboveBar' } // DARK_POOL
}

/** C2.tooltip_ref = event_id ile ayni; cagiran taraf marker.id'den KoyfinOlay'i geri cozer. */
export function olaylardanMarkerUret(olaylar: KoyfinOlay[]): KoyfinLwcMarker[] {
  return olaylar.map((olay) => {
    const { shape, position } = yonSekliVeKonumu(olay)
    return {
      // V-002 COZULDU: marker aciklama/dosyalama tarihinde gosterilir,
      // gercek islem tarihinde DEGIL - piyasa olayi ACIKLANDIGI an gorur.
      time: utcMsToIsGunuString(olay.kaynak_zamani_utc),
      position,
      shape,
      color: RENK[olay.tip],
      text: olay.tip,
      id: olay.id,
    }
  })
}

/** Ayni gune dusen coklu olay -> tek gorsel marker'a kumelenir (FAZ 3
 * gorsel-gurultu onlemi). Kumelenen olaylarin id'leri tooltip'in
 * hepsini listeleyebilmesi icin bir yan-tabloda tutulur. */
export function markerlariKumele(
  markers: KoyfinLwcMarker[]
): { gorunen: KoyfinLwcMarker[]; kumeHaritasi: Map<string, string[]> } {
  const gunBasinaGrup = new Map<string, KoyfinLwcMarker[]>()
  for (const m of markers) {
    const anahtar = `${m.time}|${m.position}`
    if (!gunBasinaGrup.has(anahtar)) gunBasinaGrup.set(anahtar, [])
    gunBasinaGrup.get(anahtar)!.push(m)
  }
  const gorunen: KoyfinLwcMarker[] = []
  const kumeHaritasi = new Map<string, string[]>()
  for (const grup of gunBasinaGrup.values()) {
    const temsilci = grup[0]
    const idListesi = grup.map((m) => m.id)
    kumeHaritasi.set(temsilci.id, idListesi)
    gorunen.push(
      grup.length === 1
        ? temsilci
        : { ...temsilci, text: `${temsilci.text} +${grup.length - 1}` }
    )
  }
  return { gorunen, kumeHaritasi }
}
