'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      router.push('/dashboard')
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <form onSubmit={handleLogin} style={{ background: '#1e293b', padding: 40, borderRadius: 12, width: 340 }}>
        <h1 style={{ color: '#D4AF37', marginBottom: 24 }}>ALPHAWISE</h1>
        <input
          type="email" placeholder="E-posta" value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ width: '100%', padding: 10, marginBottom: 12, borderRadius: 6, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0' }}
          required
        />
        <input
          type="password" placeholder="Sifre" value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ width: '100%', padding: 10, marginBottom: 16, borderRadius: 6, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0' }}
          required
        />
        {error && <p style={{ color: '#f87171', fontSize: 14 }}>{error}</p>}
        <button type="submit" disabled={loading}
          style={{ width: '100%', padding: 12, borderRadius: 6, border: 'none', background: '#D4AF37', color: '#0f172a', fontWeight: 'bold', cursor: 'pointer' }}>
          {loading ? 'Giris yapiliyor...' : 'Giris Yap'}
        </button>
      </form>
    </div>
  )
}
