'use client'
/**
 * Portfoy performans grafigi (Madde 30) — GERCEK defterden.
 *
 * UC DEGISMEZ KURAL
 * =================
 * 1. Olculemeyen noktadan CIZGI GECMEZ; kirilir. Atlayarak gecmek,
 *    olculmemis bir araligi olculmus gibi gostermek olurdu.
 * 2. Verinin TAZELIGI acikca yazilir. Canli olcumde (08.09.2026) merkezi
 *    fiyat deposunun en yeni gunu 09-03'tu; grafik sessizce orada bitip
 *    "guncel deger" gibi okunuyordu.
 * 3. Defterin SINIRLARI gizlenmez: satis yoksa "gerceklesmis kar/zarar
 *    hesaplanamaz", islem sayisi azsa "istatistiksel olarak yetersiz" yazar.
 *
 * Geometri saf ve testli: src/lib/portfoy-grafik.js (11 test, 6 mutasyon).
 */
import { useEffect, useState } from 'react'
import { parcalar, yol, kademeler, paraKisa, KENAR } from '@/lib/portfoy-grafik.js'

const RENK = { yuzey: '#1e293b', cizgi: '#334155', izgara: '#2f3f55',
               maliyet: '#94a3b8', deger: '#D4AF37', metin: '#e2e8f0',
               ikincil: '#94a3b8', soluk: '#64748b', uyari: '#fb923c',
               hata: '#f87171' }
const EN = 640, BOY = 200

// `veri` verilirse ag cagrisi YAPILMAZ. Bu, bileseni gercek veriyle ama
// oturum gerektirmeden onizleyip gorsel olarak dogrulamak icindir; uretimde
// prop verilmez ve bilesen kendi verisini ceker.
export default function PortfoyGrafigi({ veri }: { veri?: any } = {}) {
  const [d, setD] = useState<any>(veri || null)
  const [hata, setHata] = useState('')

  useEffect(() => {
    if (veri) return
    let iptal = false
    fetch('/api/portfoy').then((r) => r.json())
      .then((v) => { if (!iptal) { v?.hata ? setHata(v.hata) : setD(v) } })
      .catch((e) => { if (!iptal) setHata('Portföy servisine ulaşılamıyor: ' + e.message) })
    return () => { iptal = true }
  }, [veri])

  if (hata) {
    return (
      <div style={{ marginTop: 24 }}>
        <h3 style={{ margin: '0 0 8px', color: RENK.metin }}>Portföy Performansı</h3>
        <div style={{ background: RENK.yuzey, border: `1px solid ${RENK.cizgi}`,
                      borderRadius: 8, padding: 16, color: RENK.hata, fontSize: 13 }}>
          {hata}
        </div>
      </div>
    )
  }
  if (!d) return null

  const noktalar = (d.seri?.noktalar || []).map((n: any) => ({
    gun: n.gun, maliyet: n.maliyet, deger: n.piyasa_degeri,
  }))
  const p = parcalar(noktalar, { genislik: EN, yukseklik: BOY })
  const tumDeger = noktalar.flatMap((n: any) => [n.maliyet, n.deger])
  const kad = kademeler(tumDeger, 4)
  const t = d.tazelik || {}
  const o = d.ozet || {}

  return (
    <div style={{ marginTop: 24 }}>
      <h3 style={{ margin: '0 0 4px', color: RENK.metin }}>Portföy Performansı</h3>
      <p style={{ color: RENK.soluk, fontSize: 12, margin: '0 0 10px' }}>
        Kâğıt işlem defterinden ({o.islem_sayisi} işlem, {o.sembol_sayisi} sembol).
        Karar kodu üretilmez.
      </p>

      {t.taze_mi === false && (
        <div style={{ background: 'rgba(251,146,60,0.08)', border: `1px solid ${RENK.uyari}`,
                      borderRadius: 6, padding: '8px 10px', marginBottom: 10,
                      color: '#fdba74', fontSize: 11, lineHeight: 1.5 }}>
          {t.gerekce}
        </div>
      )}

      {noktalar.length === 0 ? (
        <div style={{ background: RENK.yuzey, border: `1px solid ${RENK.cizgi}`,
                      borderRadius: 8, padding: 16, color: RENK.soluk, fontSize: 13 }}>
          {d.seri?.gerekce || 'Seri üretilemedi.'}
        </div>
      ) : (
        <div style={{ background: RENK.yuzey, border: `1px solid ${RENK.cizgi}`,
                      borderRadius: 8, padding: 12, overflowX: 'auto' }}>
          <svg viewBox={`0 0 ${EN} ${BOY}`} role="img"
               aria-label={`Portföy maliyet ve piyasa değeri, ${noktalar.length} gün`}
               style={{ width: '100%', minWidth: 420, height: 'auto' }}>
            {kad.map((k: number, i: number) => {
              const y = KENAR.ust + (BOY - KENAR.ust - KENAR.alt) *
                (1 - (k - Math.min(...kad)) / ((Math.max(...kad) - Math.min(...kad)) || 1))
              return (
                <g key={i}>
                  <line x1={KENAR.sol} y1={y} x2={EN - KENAR.sag} y2={y}
                        stroke={RENK.izgara} strokeWidth={1} />
                  <text x={KENAR.sol - 6} y={y + 3} textAnchor="end"
                        fill={RENK.soluk} fontSize={9}>{paraKisa(k)}</text>
                </g>
              )
            })}
            {p.maliyet.map((parca: any, i: number) => (
              <polyline key={`m${i}`} points={yol(parca)} fill="none"
                        stroke={RENK.maliyet} strokeWidth={2} strokeDasharray="4 3" />
            ))}
            {p.deger.map((parca: any, i: number) => (
              <polyline key={`d${i}`} points={yol(parca)} fill="none"
                        stroke={RENK.deger} strokeWidth={2} />
            ))}
            {p.deger.flat().map((q: any, i: number) => (
              <circle key={i} cx={q.x} cy={q.y} r={2.5} fill={RENK.deger} />
            ))}
            {noktalar.length > 0 && (
              <>
                <text x={KENAR.sol} y={BOY - 6} fill={RENK.soluk} fontSize={9}>
                  {noktalar[0].gun}
                </text>
                <text x={EN - KENAR.sag} y={BOY - 6} textAnchor="end"
                      fill={RENK.soluk} fontSize={9}>
                  {noktalar[noktalar.length - 1].gun}
                </text>
              </>
            )}
          </svg>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 6 }}>
            <span style={{ color: RENK.ikincil, fontSize: 10 }}>
              <svg width="14" height="8" style={{ verticalAlign: 'middle' }}>
                <line x1="0" y1="4" x2="14" y2="4" stroke={RENK.deger} strokeWidth="2" />
              </svg> piyasa değeri
            </span>
            <span style={{ color: RENK.ikincil, fontSize: 10 }}>
              <svg width="14" height="8" style={{ verticalAlign: 'middle' }}>
                <line x1="0" y1="4" x2="14" y2="4" stroke={RENK.maliyet}
                      strokeWidth="2" strokeDasharray="3 2" />
              </svg> maliyet
            </span>
            <span style={{ color: RENK.soluk, fontSize: 10 }}>
              çizgideki boşluk = o gün ölçülemedi (sıfır değil)
            </span>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 10 }}>
        <Kutu etiket="Maliyet" deger={o.son_maliyet} />
        <Kutu etiket="Piyasa değeri" deger={o.son_piyasa_degeri} />
        <Kutu etiket="Gerçekleşmemiş K/Z" deger={o.son_gerceklesmemis_kz}
              renkli />
      </div>

      <details style={{ marginTop: 10 }}>
        <summary style={{ color: RENK.soluk, fontSize: 11, cursor: 'pointer' }}>
          Bu grafiğin söyleyemedikleri
        </summary>
        <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          {(o.sinirlar || []).map((s: string, i: number) => (
            <li key={i} style={{ color: RENK.ikincil, fontSize: 11, marginTop: 2 }}>{s}</li>
          ))}
        </ul>
      </details>
    </div>
  )
}

function Kutu({ etiket, deger, renkli }: any) {
  const yok = deger === null || deger === undefined
  const renk = !renkli || yok ? '#e2e8f0' : (deger >= 0 ? '#4ade80' : '#f87171')
  return (
    <div style={{ background: '#1e293b', border: '1px solid #334155',
                  borderRadius: 8, padding: '8px 14px', minWidth: 120 }}>
      <div style={{ color: '#64748b', fontSize: 10 }}>{etiket}</div>
      <div style={{ color: renk, fontSize: 16, fontWeight: 'bold' }}>
        {yok ? '—' : deger.toLocaleString('tr-TR', { maximumFractionDigits: 2 })}
      </div>
    </div>
  )
}
