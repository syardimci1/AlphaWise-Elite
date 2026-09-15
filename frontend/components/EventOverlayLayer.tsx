'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import { createSeriesMarkers, IChartApi, ISeriesApi, ISeriesMarkersPluginApi, Time } from 'lightweight-charts'
import {
  congressOlaylari, insiderOlaylari, darkPoolOlaylari, onucFOlaylari,
  olaylariTekillestir, KoyfinOlay, KoyfinOlayTipi,
} from '../src/lib/koyfin-olaylar'
import { olaylardanMarkerUret, markerlariKumele } from '../src/lib/koyfin-marker'
import { utcMsToYerelEtiket } from '../src/lib/koyfin-zaman'

// Koyfin Olay Katmani (FAZ 2, contracts/C1-C5).
//
// Y4 (canli karar yolu dokunulmaz): bu bilesen YALNIZCA 4 salt-okuma
// GET cagirir ve grafik uzerine GORSEL marker cizer. Hicbir POST/PUT/
// DELETE yapmaz, hicbir sinyal/karar/emir modulunu import ETMEZ -
// asagidaki import listesi bunun kod-kaniti: yalnizca lightweight-charts
// ve kendi koyfin-* saf fonksiyonlari.
//
// Y5 (mevcut render akisini bozmadan bindirme): PriceChart.tsx'in
// KENDI candle render'ina hicbir sekilde MUDAHALE ETMEZ - yalnizca
// disaridan verilen chart/series referansina createSeriesMarkers ile
// EKLENTI yapar (lightweight-charts'in resmi eklenti API'si, FAZ 1'de
// canli dogrulandi).
const TUM_TIPLER: KoyfinOlayTipi[] = ['13F', 'DARK_POOL', 'CONGRESS', 'INSIDER']

type Props = {
  symbol: string
  chart: IChartApi
  series: ISeriesApi<'Candlestick'>
}

function urldenAktifTipler(): Set<KoyfinOlayTipi> {
  const s = new Set<KoyfinOlayTipi>(TUM_TIPLER)
  if (typeof window === 'undefined') return s
  const params = new URLSearchParams(window.location.search)
  for (const tip of TUM_TIPLER) {
    // C.Filtre kurali: durum URL query'de, localStorage'da DEGIL.
    // Varsayilan ACIK - yalnizca '0' ile acikca kapatilir (paylasilan
    // bir link filtresiz haliyle TUM olaylari gostermeli).
    if (params.get(`olay_${tip.toLowerCase()}`) === '0') s.delete(tip)
  }
  return s
}

function onizlemeTokeniUrlden(): string | null {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.search).get('koyfin_preview')
}

export default function EventOverlayLayer({ symbol, chart, series }: Props) {
  const [bayrakAcik, setBayrakAcik] = useState<boolean | null>(null) // null = henuz bilinmiyor
  const [olaylar, setOlaylar] = useState<KoyfinOlay[]>([])
  const [aktifTipler, setAktifTipler] = useState<Set<KoyfinOlayTipi>>(() => urldenAktifTipler())
  const [secili, setSecili] = useState<KoyfinOlay[] | null>(null)

  const markerApiRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const olayHaritasiRef = useRef<Map<string, KoyfinOlay>>(new Map())
  const kumeHaritasiRef = useRef<Map<string, string[]>>(new Map())

  // 1) BAYRAK KONTROLU - her seyden once. Kapaliysa asagidaki hicbir
  // useEffect calismaz (hepsi bayrakAcik'a bagli) - "kapaliyken sifir
  // maliyet" iddiasinin kod-kaniti (bkz. bench/overlay_bench.md).
  useEffect(() => {
    let iptal = false
    const token = onizlemeTokeniUrlden()
    const yol = token ? `/api/config/koyfin-flag?koyfin_preview=${encodeURIComponent(token)}` : '/api/config/koyfin-flag'
    fetch(yol)
      .then((r) => r.json())
      .then((d) => { if (!iptal) setBayrakAcik(Boolean(d.enabled)) })
      .catch(() => { if (!iptal) setBayrakAcik(false) })
    return () => { iptal = true }
  }, [])

  // 2) Bayrak aciksa 4 kaynagi paralel cek (Y2: mevcut 4 uc disinda YOK)
  useEffect(() => {
    if (!bayrakAcik) return
    let iptal = false
    const gec = (url: string) => fetch(url).then((r) => (r.ok ? r.json() : null)).catch(() => null)
    Promise.all([
      gec(`/api/congress-trading/${symbol}`),
      gec(`/api/insider-trading/${symbol}`),
      gec(`/api/finra-darkpool-regsho/${symbol}`),
      gec(`/api/sec-edgar-13f/${symbol}`),
    ]).then(([congressYanit, insiderYanit, darkPoolYanit, onucFYanit]) => {
      if (iptal) return
      setOlaylar(olaylariTekillestir([
        ...congressOlaylari(symbol, congressYanit?.trades || []),
        ...insiderOlaylari(symbol, insiderYanit?.kayitlar || []),
        ...darkPoolOlaylari(symbol, darkPoolYanit),
        ...onucFOlaylari(symbol, onucFYanit?.sahipler || []),
      ]))
    })
    return () => { iptal = true }
  }, [bayrakAcik, symbol])

  // 3) Filtrelenmis olaylardan marker uret, series'e uygula
  useEffect(() => {
    if (!bayrakAcik) return
    const filtreli = olaylar.filter((o) => aktifTipler.has(o.tip))
    olayHaritasiRef.current = new Map(filtreli.map((o) => [o.id, o]))
    const markers = olaylardanMarkerUret(filtreli)
    const { gorunen, kumeHaritasi } = markerlariKumele(markers)
    kumeHaritasiRef.current = kumeHaritasi
    if (!markerApiRef.current) {
      markerApiRef.current = createSeriesMarkers(series, gorunen)
    } else {
      markerApiRef.current.setMarkers(gorunen)
    }
  }, [olaylar, aktifTipler, bayrakAcik, series])

  // 4) Tiklama -> tooltip. CANLI DOGRULANDI (bkz. contracts/FAZ2_KANIT.md):
  // MouseEventParams.hoveredObjectId, marker olusturulurken verilen
  // 'id' alanini dondurur.
  useEffect(() => {
    if (!bayrakAcik) return
    const isleyici = (param: any) => {
      const id = param?.hoveredObjectId as string | undefined
      if (!id) { setSecili(null); return }
      const idListesi = kumeHaritasiRef.current.get(id) || [id]
      const secilenler = idListesi
        .map((i) => olayHaritasiRef.current.get(i))
        .filter((o): o is KoyfinOlay => Boolean(o))
      setSecili(secilenler.length > 0 ? secilenler : null)
    }
    chart.subscribeClick(isleyici)
    return () => chart.unsubscribeClick(isleyici)
  }, [chart, bayrakAcik])

  const tipDegistir = useCallback((tip: KoyfinOlayTipi, acikMi: boolean) => {
    setAktifTipler((onceki) => {
      const yeni = new Set(onceki)
      acikMi ? yeni.add(tip) : yeni.delete(tip)
      return yeni
    })
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      if (acikMi) params.delete(`olay_${tip.toLowerCase()}`)
      else params.set(`olay_${tip.toLowerCase()}`, '0')
      const yeniUrl = `${window.location.pathname}?${params.toString()}`
      window.history.replaceState(null, '', yeniUrl)
    }
  }, [])

  if (!bayrakAcik) return null // KAPALIYKEN: fetch yok, DOM yok, hesap yok

  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', gap: 12, fontSize: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        {TUM_TIPLER.map((tip) => (
          <label key={tip} style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={aktifTipler.has(tip)}
              onChange={(e) => tipDegistir(tip, e.target.checked)}
            />
            {tip}
          </label>
        ))}
      </div>
      {secili && secili.length > 0 && (
        <div style={{ border: '1px solid #ddd', borderRadius: 6, padding: 10, fontSize: 13, maxWidth: 420 }}>
          {secili.map((o) => (
            <div key={o.id} style={{ marginBottom: 6 }}>
              <strong>{o.tip}</strong> — {o.ozet}
              <div style={{ color: '#666', fontSize: 11 }}>
                Olay: {utcMsToYerelEtiket(o.ts_utc)} · Açıklama: {utcMsToYerelEtiket(o.kaynak_zamani_utc)} · güven: {o.confidence}
              </div>
              {o.detay_url && (
                <a href={o.detay_url} target="_blank" rel="noreferrer">Kaynağı gör</a>
              )}
            </div>
          ))}
          <button onClick={() => setSecili(null)}>Kapat</button>
        </div>
      )}
    </div>
  )
}
