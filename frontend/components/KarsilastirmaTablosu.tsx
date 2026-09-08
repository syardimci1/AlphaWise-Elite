'use client'
/**
 * Cok sembollu karsilastirma tablosu (Madde 29).
 *
 * TASARIM KARARLARI — hepsi OLCUME dayali
 * =======================================
 * 1. Tarayici TEK istek yapar (/api/karsilastir). Tek sembollu dashboard
 *    acilisi zaten 11 es zamanli istek harciyor ve hiz sinirinin anlik
 *    patlama tavani 35; N sembol x M servis cagiran bir ekran kendi kendini
 *    429'a dusururdu.
 * 2. Tabloda YALNIZCA olculerek hizli ve kotasiz oldugu dogrulanan alanlar
 *    var. Yavas veya ucretli uclar bilerek disarida ve bu ciktida ACIKCA
 *    yaziyor — gizli bir eksiklik degil, belgelenmis bir sinir.
 * 3. Bos hucre "olculemedi" demektir, SIFIR degil. Servis hatasi hucrenin
 *    altinda gerekcesiyle gorunur.
 * 4. Dar ekranda tablo YATAY KAYAR (overflowX), sayfa kaymaz.
 */
import { useState } from 'react'
import { sembolleriAyristir, girdiUyarilari, hucre, AZAMI_SEMBOL }
  from '@/lib/karsilastirma-girdi.js'

const RENK = { yuzey: '#1e293b', cizgi: '#334155', vurgu: '#D4AF37',
               metin: '#e2e8f0', ikincil: '#94a3b8', soluk: '#64748b',
               hata: '#f87171' }

const SUTUNLAR: { anahtar: string; ad: string; basamak?: number; ipucu?: string }[] = [
  { anahtar: 'son_kapanis', ad: 'Son kapanış', basamak: 2 },
  { anahtar: 'qlib_skoru', ad: 'Qlib skoru', basamak: 6,
    ipucu: 'Günlük önbellekten; karar zincirine bağlı değildir.' },
  { anahtar: 'rsi_14', ad: 'RSI-14', basamak: 1 },
  { anahtar: 'sma_20', ad: 'SMA-20', basamak: 2 },
  { anahtar: 'sma_50', ad: 'SMA-50', basamak: 2 },
  { anahtar: 'dpke_yuzde', ad: 'DPKE %', basamak: 2,
    ipucu: 'Dark Pool Katılım Endeksi; resmî DIX DEĞİLDİR.' },
  { anahtar: 'ats_hisse', ad: 'ATS hisse', basamak: 0 },
]

export default function KarsilastirmaTablosu() {
  const [girdi, setGirdi] = useState('')
  const [veri, setVeri] = useState<any>(null)
  const [hata, setHata] = useState('')
  const [yukleniyor, setYukleniyor] = useState(false)

  const onIzleme = sembolleriAyristir(girdi)
  const uyarilar = girdiUyarilari(onIzleme)

  async function calistir(e: any) {
    e.preventDefault()
    if (!onIzleme.semboller.length) return
    setYukleniyor(true); setHata(''); setVeri(null)
    try {
      const r = await fetch(`/api/karsilastir?semboller=${onIzleme.semboller.join(',')}`)
      const d = await r.json()
      d?.hata ? setHata(d.hata) : setVeri(d)
    } catch (err: any) {
      setHata('Karşılaştırma servisine ulaşılamıyor: ' + err.message)
    }
    setYukleniyor(false)
  }

  return (
    <div style={{ marginTop: 24 }}>
      <h3 style={{ margin: '0 0 4px', color: RENK.metin }}>Çoklu Sembol Karşılaştırma</h3>
      <p style={{ color: RENK.soluk, fontSize: 12, margin: '0 0 12px' }}>
        En fazla {AZAMI_SEMBOL} sembol. Yalnızca ölçülerek hızlı ve kotasız
        olduğu doğrulanan kaynaklar kullanılır; karar kodu üretilmez.
      </p>

      <form onSubmit={calistir} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input
          type="text" value={girdi} onChange={(e) => setGirdi(e.target.value)}
          placeholder="MSFT, NVDA, AMD"
          style={{ flex: 1, minWidth: 0, padding: 12, borderRadius: 8,
                   border: `1px solid ${RENK.cizgi}`, background: RENK.yuzey,
                   color: RENK.metin, fontSize: 16 }} />
        <button type="submit" disabled={yukleniyor || !onIzleme.semboller.length}
          style={{ padding: '12px 20px', borderRadius: 8, border: 'none',
                   background: RENK.vurgu, color: '#0f172a', fontWeight: 'bold',
                   cursor: 'pointer', flexShrink: 0 }}>
          {yukleniyor ? 'Karşılaştırılıyor...' : 'Karşılaştır'}
        </button>
      </form>

      {uyarilar.map((u, i) => (
        <div key={i} style={{ color: '#fdba74', fontSize: 11, marginTop: 6 }}>{u}</div>
      ))}
      {hata && <div style={{ color: RENK.hata, fontSize: 13, marginTop: 8 }}>{hata}</div>}

      {veri && (
        <>
          {/* Dar ekranda TABLO kayar, sayfa kaymaz. */}
          <div style={{ overflowX: 'auto', marginTop: 12,
                        border: `1px solid ${RENK.cizgi}`, borderRadius: 8 }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 560 }}>
              <thead>
                <tr style={{ background: RENK.yuzey }}>
                  <th style={basTd}>Sembol</th>
                  {SUTUNLAR.map((s) => (
                    <th key={s.anahtar} style={basTd} title={s.ipucu || ''}>
                      {s.ad}{s.ipucu ? ' *' : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {veri.satirlar.map((r: any) => (
                  <tr key={r.ticker} style={{ borderTop: `1px solid ${RENK.cizgi}` }}>
                    <td style={{ ...td, color: RENK.vurgu, fontWeight: 'bold' }}>
                      {r.ticker}
                    </td>
                    {SUTUNLAR.map((s) => {
                      const v = r[s.anahtar]
                      const olculdu = v !== null && v !== undefined
                      return (
                        <td key={s.anahtar} style={{ ...td,
                              color: olculdu ? RENK.metin : RENK.soluk }}>
                          {hucre(v, s.basamak)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Hangi servis neden yanit vermedi — gizlenmez. */}
          {veri.satirlar.some((r: any) => Object.values(r.hatalar).some(Boolean)) && (
            <div style={{ marginTop: 8 }}>
              {veri.satirlar.map((r: any) =>
                Object.entries(r.hatalar).filter(([, h]) => h).map(([k, h]) => (
                  <div key={r.ticker + k} style={{ color: RENK.soluk, fontSize: 11 }}>
                    {r.ticker} · {k}: {String(h)} — bu sütun ölçülemedi (sıfır değil)
                  </div>
                )))}
            </div>
          )}

          <div style={{ color: RENK.ikincil, fontSize: 11, marginTop: 10 }}>
            {veri.not}
          </div>
          <details style={{ marginTop: 8 }}>
            <summary style={{ color: RENK.soluk, fontSize: 11, cursor: 'pointer' }}>
              Kullanılan ve bilerek dışlanan kaynaklar
            </summary>
            <div style={{ marginTop: 6 }}>
              {veri.kaynaklar.map((k: any) => (
                <div key={k.ad} style={{ color: RENK.ikincil, fontSize: 11 }}>
                  ✓ {k.ad} ({k.uc}) — {k.not}
                </div>
              ))}
              {veri.dislanan_kaynaklar.map((d: string) => (
                <div key={d} style={{ color: RENK.soluk, fontSize: 11 }}>✕ {d}</div>
              ))}
            </div>
          </details>
        </>
      )}
    </div>
  )
}

const basTd: React.CSSProperties = {
  textAlign: 'left', padding: '8px 10px', color: '#94a3b8', fontSize: 11,
  fontWeight: 600, whiteSpace: 'nowrap',
}
const td: React.CSSProperties = {
  padding: '8px 10px', fontSize: 12, whiteSpace: 'nowrap',
}
