'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

const BOLGE_BASLIKLARI: Record<string, string> = {
  giris_bolgesi: 'Giris Bolgesi',
  ekleme_bolgesi: 'Ekleme Bolgesi',
  kademeli_kar_realizasyonu: 'Kademeli Kar Realizasyonu',
  teknik_seviyeler: 'Teknik Seviyeler',
}

function BolgeKarti({ bolgeAdi, deger }: { bolgeAdi: string; deger: any }) {
  const baslik = BOLGE_BASLIKLARI[bolgeAdi] || bolgeAdi

  // kademeli_kar_realizasyonu bir kademe dizisidir
  if (Array.isArray(deger)) {
    return (
      <div style={{ background: '#1e293b', padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', minWidth: 220 }}>
        <span style={{ color: '#D4AF37', fontSize: 12, fontWeight: 'bold' }}>{baslik}</span>
        {deger.map((kademe: any, i: number) => (
          <div key={i} style={{ color: '#e2e8f0', fontSize: 12, marginTop: 6, paddingTop: 6, borderTop: i > 0 ? '1px solid #334155' : 'none' }}>
            {kademe.kademe && <strong style={{ color: '#94a3b8' }}>{kademe.kademe}: </strong>}
            {kademe.alt != null && kademe.ust != null && <span>{kademe.alt} - {kademe.ust}</span>}
            {kademe.ifade && <div style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>{kademe.ifade}</div>}
          </div>
        ))}
      </div>
    )
  }

  // fiyat bandi: alt/ust/aciklama tasiyan bir obje
  if (deger.alt != null && deger.ust != null) {
    return (
      <div style={{ background: '#1e293b', padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', minWidth: 200 }}>
        <span style={{ color: '#D4AF37', fontSize: 12, fontWeight: 'bold' }}>{baslik}</span>
        <div style={{ color: '#e2e8f0', fontSize: 14, marginTop: 4 }}>{deger.alt} - {deger.ust}</div>
        {deger.aciklama && <div style={{ color: '#64748b', fontSize: 11, marginTop: 4 }}>{deger.aciklama}</div>}
      </div>
    )
  }

  // duz anahtar-deger haritasi (orn. teknik_seviyeler)
  return (
    <div style={{ background: '#1e293b', padding: '10px 14px', borderRadius: 8, border: '1px solid #334155', minWidth: 200 }}>
      <span style={{ color: '#D4AF37', fontSize: 12, fontWeight: 'bold' }}>{baslik}</span>
      {Object.entries(deger).map(([k, v]: any) => (
        <div key={k} style={{ color: '#94a3b8', fontSize: 12, marginTop: 4 }}>
          {k}: <span style={{ color: '#e2e8f0' }}>{String(v)}</span>
        </div>
      ))}
    </div>
  )
}

const BIST_METRIKLER = ['P/E', 'gelir_buyume_yuzde_yillik', 'net_kar_marji_yuzde']
const BIST_OPERATORLER = ['<', '>', '<=', '>=', '==']

const DENETIM_RENGI: Record<string, string> = {
  temiz: '#4ade80',
  uyari: '#fbbf24',
  eksik_veri_ile_hesaplandi: '#fb923c',
  kaynak_yetersiz: '#94a3b8',
}

function BistTickerKarti({ ticker, veri, denetim, karsilastirmaSatirlari, elemeSonucu }: any) {
  const kaynakYok = !veri || veri.sirket_bulunamadi

  return (
    <div style={{ background: '#1e293b', padding: 16, borderRadius: 8, border: '1px solid #334155', minWidth: 260, flex: '1 1 260px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#D4AF37', fontWeight: 'bold', fontSize: 15 }}>{ticker}</span>
        {denetim && (
          <span style={{ color: DENETIM_RENGI[denetim.genel_durum] || '#94a3b8', fontSize: 11, border: `1px solid ${DENETIM_RENGI[denetim.genel_durum] || '#94a3b8'}`, borderRadius: 4, padding: '2px 6px' }}>
            {denetim.genel_durum}
          </span>
        )}
      </div>

      {kaynakYok && (
        <p style={{ color: '#f87171', fontSize: 13, marginTop: 8 }}>Kaynak bulunamadı - şirket bulunamadı veya veri yok.</p>
      )}

      {!kaynakYok && veri.fiyat && (
        <p style={{ color: '#e2e8f0', fontSize: 14, margin: '8px 0 2px' }}>
          {veri.fiyat.kapanis} {veri.fiyat.para_birimi}
          <span style={{ color: '#64748b', fontSize: 11 }}> ({veri.fiyat.tarih}, {veri.fiyat.kaynak})</span>
        </p>
      )}
      {!kaynakYok && !veri.fiyat && (
        <p style={{ color: '#f87171', fontSize: 12, marginTop: 4 }}>Fiyat: Kaynak bulunamadı</p>
      )}

      {/* KISMI VERI UYARISI: veri kaynagi timeout'ta sessizce eksik donem
          dondurebiliyor; bu durumda rakamlar bayat bir doneme ait olabilir.
          Kullanici bunu panelde ACIKCA gormeli (bkz. war room bulgusu). */}
      {!kaynakYok && veri.eksik_donem_sayisi > 0 && (
        <div style={{ marginTop: 8, padding: '8px 10px', borderRadius: 6, background: '#431407', border: '1px solid #fb923c' }}>
          <div style={{ color: '#fdba74', fontSize: 12, fontWeight: 'bold' }}>
            ⚠️ Bu veri {veri.kullanilan_en_guncel_donem || 'bilinmeyen'} dönemine ait, güncel olmayabilir
          </div>
          <div style={{ color: '#fdba74', fontSize: 11, marginTop: 3 }}>
            Kaynaktan {veri.eksik_donem_sayisi} dönem eksik geldi ({veri.eksik_donemler.slice(0, 4).join(', ')}
            {veri.eksik_donemler.length > 4 ? ', …' : ''}). Aşağıdaki rakamlar bu eksik veriyle hesaplandı.
          </div>
        </div>
      )}

      {karsilastirmaSatirlari && karsilastirmaSatirlari.length > 0 && (
        <div style={{ marginTop: 10 }}>
          {karsilastirmaSatirlari.map((s: any) => (
            <div key={s.metrik} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginTop: 3 }} title={s.aciklama}>
              <span style={{ color: '#94a3b8' }}>{s.metrik}</span>
              <span style={{ color: s.kaynak_yok ? '#f87171' : '#e2e8f0' }}>
                {s.kaynak_yok ? 'Kaynak Yok' : (typeof s.deger === 'number' ? s.deger.toFixed(2) : s.deger)}
              </span>
            </div>
          ))}
        </div>
      )}

      {elemeSonucu && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #334155' }}>
          <span style={{ fontSize: 12, fontWeight: 'bold', color: elemeSonucu.gecti ? '#4ade80' : '#f87171' }}>
            {elemeSonucu.gecti ? 'KRİTERLERİ SAĞLADI' : 'KRİTERLERİ SAĞLAMADI'}
          </span>
          {elemeSonucu.nedenler.map((n: string, i: number) => (
            <div key={i} style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>{n}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function BistArastirmaMasasi() {
  const [tickerGirdi, setTickerGirdi] = useState('')
  const [kriterler, setKriterler] = useState<any[]>([])
  const [yeniMetrik, setYeniMetrik] = useState(BIST_METRIKLER[0])
  const [yeniOperator, setYeniOperator] = useState(BIST_OPERATORLER[0])
  const [yeniDeger, setYeniDeger] = useState('')
  const [sonuc, setSonuc] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [logAcik, setLogAcik] = useState(false)

  function kriterEkle() {
    if (yeniDeger.trim() === '' || isNaN(Number(yeniDeger))) return
    setKriterler([...kriterler, { metrik: yeniMetrik, operator: yeniOperator, deger: Number(yeniDeger) }])
    setYeniDeger('')
  }

  function kriterSil(i: number) {
    setKriterler(kriterler.filter((_, idx) => idx !== i))
  }

  async function arastir(e: React.FormEvent) {
    e.preventDefault()
    const tickerlar = tickerGirdi.split(',').map(t => t.trim().toUpperCase()).filter(Boolean)
    if (tickerlar.length === 0) return
    setLoading(true)
    setError('')
    setSonuc(null)
    try {
      const resp = await fetch('/api/bist-desk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickerlar, kriterler: kriterler.length > 0 ? kriterler : undefined }),
      })
      const data = await resp.json()
      if (data.error) {
        setError(data.error)
      } else {
        setSonuc(data)
      }
    } catch (err: any) {
      setError('BIST Arastirma Masasi servisine ulasilamiyor: ' + err.message)
    }
    setLoading(false)
  }

  return (
    <div style={{ marginTop: 32, background: '#1e293b', padding: 20, borderRadius: 12, border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 4px', color: '#e2e8f0' }}>BIST Arastirma Masasi</h3>
      <p style={{ color: '#64748b', fontSize: 12, marginTop: 0, marginBottom: 16 }}>
        Izole, bagimsiz sistem - God Mode/MAA karar kodlarindan etkilenmez. Gercek veri bulunamazsa
        acikca &quot;Kaynak bulunamadı&quot; gosterir, tahmini deger URETMEZ.
      </p>

      <form onSubmit={arastir} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          type="text" placeholder="Ticker(lar), virgulle ayirin (orn: THYAO, ASELS)" value={tickerGirdi}
          onChange={(e) => setTickerGirdi(e.target.value)}
          style={{ flex: 1, padding: 10, borderRadius: 8, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0' }}
        />
        <button type="submit" disabled={loading}
          style={{ padding: '10px 20px', borderRadius: 8, border: 'none', background: '#D4AF37', color: '#0f172a', fontWeight: 'bold', cursor: 'pointer' }}>
          {loading ? 'Araniyor...' : 'Arastir'}
        </button>
      </form>

      <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
        <select value={yeniMetrik} onChange={e => setYeniMetrik(e.target.value)}
          style={{ padding: 6, borderRadius: 6, background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155', fontSize: 12 }}>
          {BIST_METRIKLER.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <select value={yeniOperator} onChange={e => setYeniOperator(e.target.value)}
          style={{ padding: 6, borderRadius: 6, background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155', fontSize: 12 }}>
          {BIST_OPERATORLER.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
        <input type="number" placeholder="deger" value={yeniDeger} onChange={e => setYeniDeger(e.target.value)}
          style={{ width: 80, padding: 6, borderRadius: 6, background: '#0f172a', color: '#e2e8f0', border: '1px solid #334155', fontSize: 12 }} />
        <button type="button" onClick={kriterEkle}
          style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #D4AF37', background: 'transparent', color: '#D4AF37', fontSize: 12, cursor: 'pointer' }}>
          + Kriter Ekle
        </button>
        {kriterler.map((k, i) => (
          <span key={i} style={{ background: '#0f172a', padding: '4px 8px', borderRadius: 6, fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
            {k.metrik} {k.operator} {k.deger}
            <span onClick={() => kriterSil(i)} style={{ cursor: 'pointer', color: '#f87171' }}> ×</span>
          </span>
        ))}
      </div>

      {error && <p style={{ color: '#f87171', fontSize: 13 }}>{error}</p>}

      {sonuc && (
        <div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            {sonuc.tickerlar.map((t: string) => (
              <BistTickerKarti
                key={t}
                ticker={t}
                veri={sonuc.veri[t]}
                denetim={sonuc.denetim[t]}
                karsilastirmaSatirlari={sonuc.karsilastirma?.satirlar.filter((s: any) => s.ticker === t)}
                elemeSonucu={sonuc.eleme?.find((e: any) => e.ticker === t)}
              />
            ))}
          </div>

          <button type="button" onClick={() => setLogAcik(!logAcik)}
            style={{ marginTop: 12, background: 'transparent', border: 'none', color: '#64748b', fontSize: 11, cursor: 'pointer', textDecoration: 'underline' }}>
            {logAcik ? 'Ajan gunlugunu gizle' : 'Ajan gunlugunu goster'}
          </button>
          {logAcik && (
            <div style={{ marginTop: 8, background: '#0f172a', padding: 10, borderRadius: 6, fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>
              {sonuc.ajan_log.map((k: any, i: number) => (
                <div key={i}>[{k.zaman}] {k.ajan}: {k.adim} {k.detay && `- ${k.detay}`}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function boyutBicimle(bayt: number): string {
  if (bayt < 1024) return `${bayt} B`
  if (bayt < 1024 * 1024) return `${Math.round(bayt / 1024)} KB`
  return `${(bayt / 1024 / 1024).toFixed(1)} MB`
}

function RaporlarKarti() {
  const [raporlar, setRaporlar] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/raporlar')
      .then(r => r.json())
      .then(d => {
        if (d.error) setError(d.error)
        else setRaporlar(d.raporlar || [])
      })
      .catch(err => setError('Raporlar yuklenemedi: ' + err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ marginTop: 32, background: '#1e293b', padding: 20, borderRadius: 12, border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 4px', color: '#e2e8f0' }}>Raporlar</h3>
      <p style={{ color: '#64748b', fontSize: 12, marginTop: 0, marginBottom: 14 }}>
        Gun sonu raporlari ve kullanim kilavuzu. En yeni en ustte.
      </p>

      {loading && <p style={{ color: '#64748b', fontSize: 13 }}>Yukleniyor...</p>}
      {error && <p style={{ color: '#f87171', fontSize: 13 }}>{error}</p>}
      {!loading && !error && raporlar.length === 0 && (
        <p style={{ color: '#64748b', fontSize: 13 }}>Henuz rapor uretilmemis.</p>
      )}

      {raporlar.map((r, i) => (
        <div key={r.dosya} style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '10px 0', borderBottom: i < raporlar.length - 1 ? '1px solid #334155' : 'none',
        }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ color: '#e2e8f0', fontSize: 13 }}>{r.tur}</div>
            <div style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>
              {r.tarih || 'tarihsiz'} · {boyutBicimle(r.boyut)} · {r.dosya}
            </div>
          </div>
          <a
            href={`/api/raporlar/${encodeURIComponent(r.dosya)}`}
            download={r.dosya}
            style={{
              flexShrink: 0, marginLeft: 12, padding: '6px 14px', borderRadius: 6,
              border: '1px solid #D4AF37', color: '#D4AF37', fontSize: 12,
              textDecoration: 'none', whiteSpace: 'nowrap',
            }}
          >
            Indir
          </a>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [ticker, setTicker] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [userEmail, setUserEmail] = useState('')
  const [portfolioSignal, setPortfolioSignal] = useState<any>(null)
  const [portfolioLoading, setPortfolioLoading] = useState(false)
  const [memories, setMemories] = useState<any[]>([])
  const [godmode, setGodmode] = useState<any>(null)
  const [godmodeLoading, setGodmodeLoading] = useState(false)
  const router = useRouter()

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data }) => {
      if (!data.user) {
        router.push('/')
      } else {
        setUserEmail(data.user.email || '')
      }
    })
  }, [router])

  async function handlePortfolioSignal() {
    setPortfolioLoading(true)
    try {
      const maaUrl = process.env.NEXT_PUBLIC_MAA_URL || 'http://localhost:8005'
      const resp = await fetch(`${maaUrl}/portfolio-signal/adaptive_rotation`)
      const data = await resp.json()
      setPortfolioSignal(data)
    } catch (err: any) {
      setPortfolioSignal({ error: 'FinRL-X servisine ulasilamiyor: ' + err.message })
    }
    setPortfolioLoading(false)
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!ticker.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    setGodmode(null)
    try {
      const maaUrl = process.env.NEXT_PUBLIC_MAA_URL || 'http://localhost:8005'
      const resp = await fetch(`${maaUrl}/narrative-verified/${ticker.toUpperCase()}`)
      const data = await resp.json()
      if (data.error) {
        setError(data.error)
      } else {
        setResult(data)
      }
      // Gecmis hafiza kayitlarini da ayrica cek (paralel, ana sonucu bekletmeden)
      fetch(`${maaUrl}/memory/${ticker.toUpperCase()}`)
        .then(r => r.json())
        .then(m => setMemories(m.memories || []))
        .catch(() => setMemories([]))
    } catch (err: any) {
      setError('MAA servisine ulasilamiyor: ' + err.message)
    }
    setLoading(false)

    // God Mode olasiliksal degerlendirmesi (bolgeler + yon kodu) - MAA sonucundan
    // bagimsiz, ayri bir bolumde gosterilir; MAA'nin EKLE/TUT/BEKLE/DIKKAT ET
    // karar koduna dokunmaz.
    setGodmodeLoading(true)
    fetch(`/api/godmode/${ticker.toUpperCase()}`)
      .then(r => r.json())
      .then(g => setGodmode(g))
      .catch((err) => setGodmode({ error: 'God Mode servisine ulasilamiyor: ' + err.message }))
      .finally(() => setGodmodeLoading(false))
  }

  async function handleLogout() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/')
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <h1 style={{ color: '#D4AF37' }}>ALPHAWISE</h1>
        <div>
          <span style={{ marginRight: 16, fontSize: 14, color: '#94a3b8' }}>{userEmail}</span>
          <button onClick={handleLogout} style={{ background: 'transparent', border: '1px solid #334155', color: '#e2e8f0', padding: '6px 12px', borderRadius: 6, cursor: 'pointer' }}>
            Cikis
          </button>
        </div>
      </div>

      <div style={{ marginBottom: 32, background: '#1e293b', padding: 20, borderRadius: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0, color: '#e2e8f0' }}>Portfoy Rotasyon Sinyali</h3>
          <button onClick={handlePortfolioSignal} disabled={portfolioLoading}
            style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid #D4AF37', background: 'transparent', color: '#D4AF37', cursor: 'pointer' }}>
            {portfolioLoading ? 'Hesaplaniyor...' : 'Sinyali Getir'}
          </button>
        </div>
        {portfolioSignal && portfolioSignal.error && (
          <p style={{ color: '#f87171', margin: 0 }}>{portfolioSignal.error}</p>
        )}
        {portfolioSignal && portfolioSignal.signal && (
          <div>
            <p style={{ color: '#94a3b8', margin: '4px 0' }}>
              Piyasa Rejimi: <strong style={{ color: '#e2e8f0' }}>{portfolioSignal.signal.market_regime}</strong>
              {' | '}Yatirim Orani: <strong style={{ color: '#e2e8f0' }}>%{portfolioSignal.signal.total_invested_pct}</strong>
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
              {portfolioSignal.signal.target_portfolio && Object.entries(portfolioSignal.signal.target_portfolio).map(([ticker, pct]: any) => (
                <div key={ticker} style={{ background: '#0f172a', padding: '8px 14px', borderRadius: 8, border: '1px solid #334155' }}>
                  <span style={{ color: '#D4AF37', fontWeight: 'bold' }}>{ticker}</span>
                  <span style={{ color: '#94a3b8', marginLeft: 8 }}>%{pct}</span>
                </div>
              ))}
            </div>
            <p style={{ color: '#64748b', fontSize: 12, marginTop: 12, marginBottom: 0 }}>
              Sadece sinyal - gercek islem yapilmaz.
            </p>
          </div>
        )}
      </div>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 32 }}>
        <input
          type="text" placeholder="Hisse kodu girin (orn: NVDA)" value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          style={{ flex: 1, padding: 14, borderRadius: 8, border: '1px solid #334155', background: '#1e293b', color: '#e2e8f0', fontSize: 16 }}
        />
        <button type="submit" disabled={loading}
          style={{ padding: '14px 28px', borderRadius: 8, border: 'none', background: '#D4AF37', color: '#0f172a', fontWeight: 'bold', cursor: 'pointer' }}>
          {loading ? 'Analiz ediliyor...' : 'Analiz Et'}
        </button>
      </form>

      {loading && <p style={{ color: '#94a3b8' }}>Analiz suruyor, bu 60-90 saniye surebilir (3 asamali dogrulama)...</p>}
      {error && <p style={{ color: '#f87171' }}>{error}</p>}

      {result && result.cascade_meta && !result.cascade_meta.constitution_check?.clear && (
        <div style={{ background: '#7f1d1d', padding: 16, borderRadius: 8, marginBottom: 16, color: '#fecaca' }}>
          <strong>Kalite Uyarisi:</strong> Bu rapor, sistemin kendi ic doğrulamasindan tam gecemedi
          ({result.cascade_meta.retry_count || 0} duzeltme denemesi yapildi).
          Tespit edilen sorunlar: {result.cascade_meta.constitution_check?.issues?.join(', ')}.
          Lutfen icerigi daha dikkatli degerlendirin.
        </div>
      )}
      {result && (
        <div style={{ background: '#1e293b', padding: 24, borderRadius: 12, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
          {result.narrative}
        </div>
      )}
      {(godmodeLoading || godmode) && (
        <div style={{ marginTop: 24, background: '#0f172a', padding: 20, borderRadius: 12, border: '1px solid #334155' }}>
          <h4 style={{ color: '#94a3b8', marginTop: 0 }}>God Mode - Olasiliksal Degerlendirme</h4>
          {godmodeLoading && <p style={{ color: '#64748b', fontSize: 14 }}>Bolgeler ve yon olasiligi hesaplaniyor...</p>}
          {!godmodeLoading && godmode?.error && (
            <p style={{ color: '#f87171', fontSize: 14, margin: 0 }}>{godmode.error}</p>
          )}
          {!godmodeLoading && godmode && !godmode.error && (
            <div>
              <p style={{ color: '#e2e8f0', margin: '4px 0', fontSize: 15 }}>
                <strong style={{ color: '#D4AF37' }}>{godmode.karar_kodu}</strong>
              </p>
              {godmode.karar_gerekcesi && (
                <p style={{ color: '#94a3b8', margin: '4px 0', fontSize: 13 }}>{godmode.karar_gerekcesi}</p>
              )}
              {godmode.gunluk_yon_olasiligi && (
                <p style={{ color: '#94a3b8', margin: '10px 0 4px', fontSize: 13 }}>
                  Yukari yon olasiligi: <strong style={{ color: '#e2e8f0' }}>%{Math.round((godmode.gunluk_yon_olasiligi.yukari ?? 0) * 100)}</strong>
                  {' | '}Kalibrasyon: <strong style={{ color: '#e2e8f0' }}>
                    {godmode.gunluk_yon_olasiligi.kalibrasyon_kaniti?.gecerli ? 'dogrulanmis' : 'dogrulanmamis'}
                  </strong>
                </p>
              )}
              {godmode.fiyat_bolgeleri?.hesaplanabildi !== false && godmode.fiyat_bolgeleri && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                  {Object.entries(godmode.fiyat_bolgeleri).map(([bolgeAdi, bolgeDeger]: any) => {
                    if (typeof bolgeDeger !== 'object' || bolgeDeger === null) return null
                    return <BolgeKarti key={bolgeAdi} bolgeAdi={bolgeAdi} deger={bolgeDeger} />
                  })}
                </div>
              )}
              {godmode.mevcut_fiyat_konumu && (
                <p style={{ color: '#64748b', fontSize: 12, marginTop: 10, marginBottom: 0 }}>
                  Mevcut fiyat konumu: {godmode.mevcut_fiyat_konumu}
                </p>
              )}
              <p style={{ color: '#64748b', fontSize: 11, marginTop: 10, marginBottom: 0 }}>
                {godmode.kapsam_notu}
              </p>
            </div>
          )}
        </div>
      )}
      {memories.length > 0 && (
        <div style={{ marginTop: 24, background: '#0f172a', padding: 20, borderRadius: 12, border: '1px solid #334155' }}>
          <h4 style={{ color: '#94a3b8', marginTop: 0 }}>Gecmis Kayitlar (Hafiza)</h4>
          {memories.map((m, i) => (
            <div key={i} style={{ padding: '10px 0', borderBottom: i < memories.length - 1 ? '1px solid #1e293b' : 'none' }}>
              <p style={{ color: '#e2e8f0', margin: 0, fontSize: 14 }}>{m.text}</p>
            </div>
          ))}
        </div>
      )}

      <BistArastirmaMasasi />
      <RaporlarKarti />
    </div>
  )
}
