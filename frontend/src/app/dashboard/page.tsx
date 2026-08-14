'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

export default function Dashboard() {
  const [ticker, setTicker] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [userEmail, setUserEmail] = useState('')
  const [portfolioSignal, setPortfolioSignal] = useState<any>(null)
  const [portfolioLoading, setPortfolioLoading] = useState(false)
  const [memories, setMemories] = useState<any[]>([])
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
    </div>
  )
}
