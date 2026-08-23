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

// ---------------------------------------------------------------------------
// PIYASA SINYALLERI
// ---------------------------------------------------------------------------
// Yedi bagimsiz veri servisini tek bolumde toplar. TASARIM ILKESI: bir servis
// calismiyorsa ya da verisi dogrulanmamissa bu GIZLENMEZ; God Mode kartindaki
// "kalibrasyon: dogrulanmamis" deseniyle ayni durustlukte, nedeniyle birlikte
// yazilir. Hicbir sinyal icin al/sat yonunde ifade kullanilmaz — yalnizca
// olculen veri ve o verinin siniri aktarilir.

type SinyalDurumu = 'yukleniyor' | 'veri' | 'hata'

function DurumRozeti({ metin, renk }: { metin: string; renk: string }) {
  return (
    <span style={{
      fontSize: 10, padding: '2px 8px', borderRadius: 10, whiteSpace: 'nowrap',
      border: `1px solid ${renk}`, color: renk, marginLeft: 8,
    }}>
      {metin}
    </span>
  )
}

function SinyalKutusu({
  baslik, aciklama, rozet, rozetRenk, durum, hata, children, uyari,
}: {
  baslik: string
  aciklama: string
  rozet?: string
  rozetRenk?: string
  durum: SinyalDurumu
  hata?: string
  children?: React.ReactNode
  uyari?: string
}) {
  return (
    <div style={{
      background: '#0f172a', border: '1px solid #334155', borderRadius: 10,
      padding: 14, marginBottom: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 600 }}>{baslik}</span>
        {rozet && <DurumRozeti metin={rozet} renk={rozetRenk || '#64748b'} />}
      </div>
      <p style={{ color: '#64748b', fontSize: 11, margin: '4px 0 10px' }}>{aciklama}</p>

      {uyari && (
        <div style={{
          background: 'rgba(251,146,60,0.08)', border: '1px solid #fb923c',
          borderRadius: 6, padding: '8px 10px', marginBottom: 10,
          color: '#fdba74', fontSize: 11, lineHeight: 1.5,
        }}>
          {uyari}
        </div>
      )}

      {durum === 'yukleniyor' && (
        <p style={{ color: '#64748b', fontSize: 12, margin: 0 }}>Yukleniyor...</p>
      )}
      {durum === 'hata' && (
        <p style={{ color: '#f87171', fontSize: 12, margin: 0 }}>{hata}</p>
      )}
      {durum === 'veri' && children}
    </div>
  )
}

function Satir({ etiket, deger }: { etiket: string; deger: React.ReactNode }) {
  // SAVUNMA: bu degerler dis servislerden geliyor. Bir servis ileride bir
  // alani sayi/metin yerine nesne olarak dondururse React "Objects are not
  // valid as a React child" ile TUM sayfayi dusururdu — yani tek bir servis
  // sema degisikligi dashboard'un tamamini beyaz ekran yapardi. Beklenmeyen
  // turleri burada metne cevirerek bu riski kutuyla sinirliyoruz.
  const guvenliDeger =
    deger === null || deger === undefined
      ? '—'
      : typeof deger === 'object' && !Array.isArray(deger) && !('type' in (deger as any))
        ? JSON.stringify(deger)
        : deger

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '3px 0' }}>
      <span style={{ color: '#94a3b8', fontSize: 12 }}>{etiket}</span>
      <span style={{ color: '#e2e8f0', fontSize: 12, textAlign: 'right' }}>{guvenliDeger}</span>
    </div>
  )
}

function sayiBicimle(n: number | null | undefined, basamak = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return n.toLocaleString('tr-TR', { maximumFractionDigits: basamak })
}

/**
 * Buyuk dolar buyukluklerini okunabilir kisaltir (opsiyon maruziyeti
 * degerleri 10^10 mertebesine cikiyor; ham basamaklar okunmuyor).
 * Isaret KORUNUR: negatif maruziyet ters yonu ifade eder, gizlenemez.
 */
function dolarBicimle(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  const mutlak = Math.abs(n)
  const isaret = n < 0 ? '-' : ''
  if (mutlak >= 1e9) return `${isaret}$${(mutlak / 1e9).toLocaleString('tr-TR', { maximumFractionDigits: 2 })} milyar`
  if (mutlak >= 1e6) return `${isaret}$${(mutlak / 1e6).toLocaleString('tr-TR', { maximumFractionDigits: 2 })} milyon`
  return `${isaret}$${mutlak.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}`
}

/** Tek bir sinyal servisini cagirip {durum, veri, hata} olarak dondurur. */
function useSinyal(url: string | null) {
  const [durum, setDurum] = useState<SinyalDurumu>('yukleniyor')
  const [veri, setVeri] = useState<any>(null)
  const [hata, setHata] = useState('')

  useEffect(() => {
    if (!url) return
    let iptal = false
    setDurum('yukleniyor')
    setVeri(null)
    setHata('')

    fetch(url)
      .then(async r => ({ ok: r.ok, govde: await r.json() }))
      .then(({ ok, govde }) => {
        if (iptal) return
        if (!ok || govde?.hata) {
          // Sessizce bos birakmiyoruz: servisin verdigi gerekce de gosteriliyor.
          const detay = govde?.detay
          const detayMetni =
            typeof detay === 'string' ? detay
              : detay ? JSON.stringify(detay).slice(0, 160)
                : ''
          setHata((govde?.hata || 'Veri alinamadi') + (detayMetni ? ` — ${detayMetni}` : ''))
          setDurum('hata')
        } else {
          setVeri(govde)
          setDurum('veri')
        }
      })
      .catch(e => {
        if (iptal) return
        setHata('Baglanti hatasi: ' + e.message)
        setDurum('hata')
      })

    return () => { iptal = true }
  }, [url])

  return { durum, veri, hata }
}

function PiyasaSinyalleri({ ticker }: { ticker: string }) {
  const t = ticker ? ticker.toUpperCase() : ''
  const sec = useSinyal(t ? `/api/sec-edgar-13f/${t}` : null)
  const kurum = useSinyal(t ? `/api/institution-filter/${t}` : null)
  const finra = useSinyal(t ? `/api/finra-darkpool/${t}` : null)
  const kongre = useSinyal(t ? `/api/congress-trading/${t}` : null)
  const dpke = useSinyal(t ? `/api/gamma-exposure/${t}` : null)
  const qlibSkor = useSinyal(t ? `/api/qlib/${t}` : null)
  // 23.08.2026 — 7. sinyal: SEC Form 4 (sirket ici yonetici islemleri).
  const iceriden = useSinyal(t ? `/api/insider-trading/${t}` : null)
  // 23.08.2026 — 8. sinyal: opsiyon maruziyeti (DEX/GEX/Vanna).
  // Zincir openbb-service uzerinden yfinance'ten gelir; FlashAlpha kotasina
  // DOKUNMAZ (ayni servisteki /gex ucu ucretsiz planda kapali ve basarisiz
  // cagri bile kotadan dusuyordu — bu kart o tuzaga girmez).
  const opsiyon = useSinyal(t ? `/api/dex-vanna/${t}` : null)
  // Likidite hisseye bagli degil; ticker olmasa da her zaman cekilir.
  const likidite = useSinyal('/api/liquidity-signal')

  return (
    <div style={{ marginTop: 32, background: '#1e293b', padding: 20, borderRadius: 12, border: '1px solid #334155' }}>
      <h3 style={{ margin: '0 0 4px', color: '#e2e8f0' }}>Piyasa Sinyalleri</h3>
      <p style={{ color: '#64748b', fontSize: 12, marginTop: 0, marginBottom: 16 }}>
        Bagimsiz veri kaynaklarindan olculen gozlemler. Bunlar bir karar ya da
        tavsiye degildir; her sinyalin kendi sinirlari asagida belirtilmistir.
        {!t && ' Hisseye bagli sinyaller icin yukaridan bir hisse kodu arayin.'}
      </p>

      {/* ---------- SEC EDGAR 13F ---------- */}
      {t && (
        <SinyalKutusu
          baslik="SEC EDGAR — Kurumsal Pozisyonlar"
          aciklama="Buyuk fonlarin ceyrek sonu itibariyla bildirdigi hisse pozisyonlari. Kaynak: SEC'in resmi acik verisi."
          rozet="ucretsiz · resmi kaynak"
          rozetRenk="#4ade80"
          durum={sec.durum}
          hata={sec.hata}
          uyari="13F verisi ceyrek sonu fotografidir ve ceyrek bitiminden 45 gun sonrasina kadar aciklanabilir; guncel pozisyonu gostermez."
        >
          {sec.veri && (
            <>
              <Satir etiket="Pozisyon bildiren kurum" deger={`${sec.veri.bulunan_kurum_sayisi ?? 0} kurum`} />
              <Satir etiket="Taranan kurum haritasi" deger={`${sec.veri.kapsam?.haritadaki_kurum ?? '—'} kurumdan ${sec.veri.kapsam?.bu_cagride_cekilen ?? '—'} tanesi`} />
              {(sec.veri.sahipler || []).slice(0, 3).map((s: any) => (
                <Satir
                  key={s.kurum_cik}
                  etiket={s.kurum}
                  deger={`${sayiBicimle(s.hisse_pozisyonu?.adet)} adet · ${s.donem}`}
                />
              ))}
              <p style={{ color: '#64748b', fontSize: 10, marginTop: 8, marginBottom: 0 }}>
                Bu SAHIPLER listesi, servisin ayrintili olarak taradigi kuratorlenmis kurum
                kumesiyle sinirlidir; hissenin tum sahiplerini gostermez. Kurum ADINDAN arama
                ise ayri bir yoldur ve SEC&apos;in resmi ceyreklik full-index&apos;inden uretilen
                8.900+ 13F dosyalayicinin tamamini kapsar (ucretsiz, anahtarsiz).
              </p>
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- SEC FORM 4 — ICERIDEN ISLEM (23.08.2026 eklendi) ---------- */}
      {t && (
        <SinyalKutusu
          baslik="SEC Form 4 — Sirket Ici Yonetici Islemleri"
          aciklama="Sirketin kendi yoneticilerinin (CEO/CFO/yonetim kurulu) kendi hisselerinde yaptigi ve SEC'e bildirdigi islemler. Sistemdeki en TAZE sahiplik akisidir: olculen yasal bildirim gecikmesi medyan 2 is gunu (13F 45 gun, Kongre 30-45 gun, dark pool 21-27 gun)."
          rozet="gozlem amacli — yon sinyali degil"
          rozetRenk="#fbbf24"
          durum={iceriden.durum}
          hata={iceriden.hata}
          uyari="Bu kutu bir yon iddiasi TASIMAZ ve tasiyamaz. Olculdu: 25 buyuk hissede 3,57 yil boyunca yalnizca 32 acik piyasa ALIMI bildirildi ve bunun 29'u tek bir hissede toplandi; 21 hissede hic alim yok. Literaturde tahmin gucu atfedilen alt kume tam da bu alimlardir, dolayisiyla orneklem yon kalibrasyonu icin matematiksel olarak yetersizdir (gereken 1.000+, eldeki ~12 gozlem). Bu nedenle servis kod seviyesinde yon kodu uretemez (lambda = 0). Ayrica kayitlarin yalnizca ucte biri kadari acik piyasa islemidir; kalani odul, opsiyon kullanimi, vergi stopaji ve hediyedir — bunlar ayristirilmistir."
        >
          {iceriden.veri && (
            <>
              <Satir etiket="Toplam Form 4 kaydi" deger={sayiBicimle(iceriden.veri.toplam_kayit)} />
              <Satir etiket="En yeni bildirim" deger={iceriden.veri.en_yeni_dosyalama || '—'} />
              <Satir etiket="Yasal gecikme (medyan)" deger={`${iceriden.veri.yasal_gecikme_is_gunu_medyan ?? '—'} is gunu`} />
              <Satir
                etiket="Son 90 gun — acik piyasa alim"
                deger={`${iceriden.veri.pencereler?.son_90_gun?.acik_piyasa_alim_islem_sayisi ?? 0} bildirim · ${iceriden.veri.pencereler?.son_90_gun?.alim_bildiren_kisi_sayisi ?? 0} kisi`}
              />
              <Satir
                etiket="Son 90 gun — acik piyasa satis"
                deger={`${iceriden.veri.pencereler?.son_90_gun?.acik_piyasa_satis_islem_sayisi ?? 0} bildirim · ${iceriden.veri.pencereler?.son_90_gun?.satis_bildiren_kisi_sayisi ?? 0} kisi`}
              />
              <Satir
                etiket="Son 180 gun — acik piyasa alim"
                deger={`${iceriden.veri.pencereler?.son_180_gun?.acik_piyasa_alim_islem_sayisi ?? 0} bildirim`}
              />
              <p style={{ color: '#64748b', fontSize: 10, marginTop: 8, marginBottom: 0 }}>
                Kaynak: SEC EDGAR Form 4 — ucretsiz ve anahtarsiz. Servis bu hisse icin
                sonucu 6 saat onbellekte tutar (SEC&apos;in toplu veri cekme uyarisi geregi).
                Kalibrasyon gecerli DEGILDIR; bu kutu MAA&apos;nin karar zincirine bagli degildir.
              </p>
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- INSTITUTION FILTER (LLMQuant) ---------- */}
      {t && (
        <SinyalKutusu
          baslik="Institution Filter — 13F (LLMQuant)"
          aciklama="Ayni 13F bilgisinin ticari bir saglayicidan (LLMQuant) gelen surumu."
          rozet="ikincil — artik gerekli degil"
          rozetRenk="#64748b"
          durum={kurum.durum}
          hata={kurum.hata}
          uyari="Bu servisin LLMQuant kredisi 0 durumunda ve yalnizca daha once onbellege dusmus hisseler yanit veriyor. ARTIK ENGEL DEGIL: kurum adindan arama, yukaridaki SEC EDGAR kutusunda ucretsiz ve sinirsiz olarak yapiliyor (SEC'in resmi ceyreklik full-index'inden uretilen 8.900+ 13F dosyalayici). Sekiz kurumla yapilan karsilastirmada iki kaynagin dondurdugu CIK'ler birebir ayni cikti; bir kurumu (Baupost Group) yalnizca ucretsiz kaynak buldu."
        >
          {kurum.veri && (
            <>
              <Satir etiket="Kapsamdaki toplam sahip" deger={sayiBicimle(kurum.veri.total_holders_in_scope)} />
              <Satir etiket="Bildirim donemi" deger={kurum.veri.ranking_period || '—'} />
              {(kurum.veri.top_holders || []).slice(0, 3).map((h: any, i: number) => (
                <Satir key={i} etiket={h.manager_name} deger={`sira ${h.manager_period_rank ?? '—'}`} />
              ))}
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- FINRA DARK POOL ---------- */}
      {t && (
        <SinyalKutusu
          baslik="FINRA — Borsa Disi (Dark Pool) Hacim"
          aciklama="Islemlerin ne kadarinin borsa disi havuzlarda gerceklestigi. Kaynak: FINRA ATS Transparency."
          rozet="ucretsiz · resmi kaynak"
          rozetRenk="#4ade80"
          durum={finra.durum}
          hata={finra.hata}
          uyari="FINRA bu veriyi HAFTALIK ve gecikmeli yayimlar; anlik piyasa gorunumu degildir."
        >
          {finra.veri && (
            <>
              <Satir etiket="Veri haftasi" deger={finra.veri.week_start_date || '—'} />
              <Satir etiket="ATS toplam hacim" deger={`${sayiBicimle(finra.veri.dark_pool?.ats_toplam_shares)} adet`} />
              <Satir etiket="ATS islem sayisi" deger={sayiBicimle(finra.veri.dark_pool?.ats_toplam_trades)} />
              <Satir etiket="Aktif ATS havuzu" deger={sayiBicimle(finra.veri.dark_pool?.aktif_ats_sayisi)} />
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- DPKE (gamma-exposure servisi) ---------- */}
      {t && (
        <SinyalKutusu
          baslik="Dark Pool Katilim Endeksi (DPKE)"
          aciklama="Borsa disi hacmin icinde dark pool havuzlarinin payi. FINRA verisinden hesaplanir."
          rozet="resmi DIX degil"
          rozetRenk="#fb923c"
          durum={dpke.durum}
          hata={dpke.hata}
          uyari="Bu gosterge SqueezeMetrics'in resmi DIX'i DEGILDIR, ona benzeyen ama farkli bir olcumdur. Ayrica ayni servisteki opsiyon GEX verisi ucretsiz FlashAlpha planinda kapali oldugu icin otomatik cagrilmaz."
        >
          {dpke.veri && (
            <>
              <Satir etiket="Cari hafta DPKE" deger={`%${dpke.veri.cari_hafta?.dpke_yuzde ?? '—'}`} />
              <Satir etiket="12 haftalik ortalama" deger={`%${dpke.veri.baglam?.ortalama_dpke_yuzde ?? '—'}`} />
              <Satir etiket="Z-skoru" deger={dpke.veri.baglam?.z_skoru ?? '—'} />
              <Satir etiket="Yuzdelik dilim" deger={`%${dpke.veri.baglam?.yuzdelik_dilim ?? '—'}`} />
              {dpke.veri.baglam?.yorum && (
                <p style={{ color: '#94a3b8', fontSize: 11, marginTop: 8, marginBottom: 0 }}>
                  {dpke.veri.baglam.yorum}
                </p>
              )}
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- OPSIYON MARUZIYETI (DEX / GEX / VANNA) ---------- */}
      {t && (
        <SinyalKutusu
          baslik="Opsiyon Maruziyeti — DEX / GEX / Vanna"
          aciklama="Opsiyon zincirinden Black-Scholes ile hesaplanan delta, gamma ve vanna maruziyeti."
          rozet="hesaplanmis turev — kalibre edilmemis"
          rozetRenk="#fbbf24"
          durum={opsiyon.durum}
          hata={opsiyon.hata}
          uyari="Bu degerler HESAPLANMIS TUREVLERDIR, olculmus bayi konumlanmasi degildir. Bayinin call'da uzun / put'ta kisa oldugu varsayimi sektorde yaygindir ama kamuya acik bir veriyle DOGRULANAMAZ; bu yuzden varsayimsiz 'ham' deger de ayrica gosterilir. Yunanlar zincirde bulunmadigi icin Black-Scholes ile hesaplanir; risksiz faiz %4 ve temettu %0 VARSAYIMDIR. Bu sinyalin ongoru gucu bu sistemde KALIBRE EDILMEMISTIR ve karar koduna baglanmaz."
        >
          {opsiyon.veri && (
            <>
              <Satir etiket="Dayanak fiyati" deger={opsiyon.veri.spot != null ? `$${sayiBicimle(opsiyon.veri.spot, 2)}` : '—'} />
              <Satir
                etiket="Hesaba giren kontrat"
                deger={`${sayiBicimle(opsiyon.veri.kullanilan_kontrat)} (elenen %${opsiyon.veri.atlanma_orani_yuzde ?? '—'})`}
              />
              <Satir etiket="Toplam acik pozisyon" deger={sayiBicimle(opsiyon.veri.toplam_acik_pozisyon)} />
              <Satir etiket="Delta maruziyeti (bayi varsayimli)" deger={dolarBicimle(opsiyon.veri.bayi_varsayimli?.dex)} />
              <Satir etiket="Gamma maruziyeti (%1 spot basina)" deger={dolarBicimle(opsiyon.veri.bayi_varsayimli?.gex)} />
              <Satir etiket="Vanna maruziyeti (1 puan IV basina)" deger={dolarBicimle(opsiyon.veri.bayi_varsayimli?.vex)} />
              <Satir
                etiket="En yogun GEX strike"
                deger={
                  opsiyon.veri.en_buyuk_gex_strike_bayi_isaretli?.[0]
                    ? `$${sayiBicimle(opsiyon.veri.en_buyuk_gex_strike_bayi_isaretli[0].strike, 2)}`
                    : '—'
                }
              />
              <Satir etiket="Ham delta maruziyeti (varsayimsiz)" deger={dolarBicimle(opsiyon.veri.ham?.dex)} />
              <p style={{ color: '#64748b', fontSize: 11, marginTop: 8, marginBottom: 0 }}>
                Kaynak: {opsiyon.veri.kaynak || '—'}
                {opsiyon.veri.onbellekten ? ' (onbellekten)' : ''}
                {' · '}FlashAlpha kotasi tuketimi: {opsiyon.veri.flashalpha_kotasi_tuketildi ? 'VAR' : 'YOK'}
              </p>
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- CONGRESS TRADING ---------- */}
      {t && (
        <SinyalKutusu
          baslik="Kongre Uyesi Islemleri"
          aciklama="ABD Kongre uyelerinin STOCK Act kapsaminda bildirdigi hisse islemleri."
          rozet={kongre.veri?.fallback_used ? 'yedek kaynak (FMP)' : 'birincil kaynak'}
          rozetRenk={kongre.veri?.fallback_used ? '#fb923c' : '#4ade80'}
          durum={kongre.durum}
          hata={kongre.hata}
          uyari="Birincil kaynak Quiver abonelik kisiti nedeniyle erisilemiyor; veri FMP yedeginden geliyor. Bildirimler islem tarihinden haftalar sonra yayimlanabilir."
        >
          {kongre.veri && (
            <>
              <Satir etiket="Bildirilen islem" deger={sayiBicimle(kongre.veri.ozet?.islem_sayisi)} />
              <Satir etiket="Alis / Satis bildirimi" deger={`${sayiBicimle(kongre.veri.ozet?.alis_sayisi)} / ${sayiBicimle(kongre.veri.ozet?.satis_sayisi)}`} />
              <Satir etiket="Farkli uye sayisi" deger={sayiBicimle(kongre.veri.ozet?.farkli_uye)} />
              <Satir etiket="Kaynak" deger={kongre.veri.source_label || kongre.veri.source || '—'} />
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- QLIB ---------- */}
      {t && (
        <SinyalKutusu
          baslik="Qlib Model Skoru"
          aciklama="LightGBM/Alpha158 modelinin hisse icin urettigi ham skor."
          rozet="dusuk tahmin gucu"
          rozetRenk="#fb923c"
          durum={qlibSkor.durum}
          hata={qlibSkor.hata}
          uyari="Modelin son egitimindeki gunluk kesitsel IC degeri 0.0123 olculdu; egitim betiginin kendi olcutune gore makul kabul edilen aralik 0.02-0.05'tir. Yani skorun tahmin gucu su an dusuktur ve tek basina bir sonuc cikarilmamalidir."
        >
          {qlibSkor.veri && (
            <>
              <Satir etiket="Skor" deger={qlibSkor.veri.score ?? '—'} />
              <Satir etiket="Skorun ait oldugu gun" deger={(qlibSkor.veri.as_of_date || '—').toString().slice(0, 10)} />
              <Satir etiket="Model" deger={qlibSkor.veri.model || '—'} />
            </>
          )}
        </SinyalKutusu>
      )}

      {/* ---------- LIQUIDITY SIGNAL (hisseden bagimsiz) ---------- */}
      <SinyalKutusu
        baslik="Fed Likidite Rejimi"
        aciklama="Fed bilancosu, Hazine hesabi ve ters repo verisinden hesaplanan net likidite. Hisseye bagli degildir."
        rozet="DOGRULANMAMIS — izleme amacli"
        rozetRenk="#f87171"
        durum={likidite.durum}
        hata={likidite.hata}
        uyari="Bu sinyal test edildi ve su an guvenilir bulunmadi: denenen 9 spesifikasyondan hicbiri gecme esigini asamadi (en iyi olculen beceri +1.63 puan, esik +5.0). Bu nedenle servis yon iddiasi tasiyan kod uretmez ve buradaki degerler yalnizca izleme/baglam amaciyla gosterilir."
      >
        {likidite.veri && (
          <>
            <Satir etiket="Rejim" deger={likidite.veri.rejim || '—'} />
            <Satir etiket="Net likidite" deger={`${sayiBicimle(likidite.veri.net_likidite_milyon_usd)} mn USD`} />
            <Satir etiket="60 gunluk Z-skor" deger={(likidite.veri.z_skor_60g ?? 0).toFixed(2)} />
            <Satir etiket="Yillik degisim" deger={`%${(likidite.veri.yoy_yuzde ?? 0).toFixed(2)}`} />
            <Satir etiket="Son veri gunu" deger={likidite.veri.son_gun || '—'} />
          </>
        )}
      </SinyalKutusu>
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
  // Arama ANINDA sabitlenen hisse kodu. Piyasa Sinyalleri bunu kullanir;
  // dogrudan `ticker` kullanilsaydi her tus vurusunda 6 servise istek giderdi.
  const [aranmisTicker, setAranmisTicker] = useState('')
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
      // Sunucu tarafi proxy: MAA'nin adresi tarayiciya sizmaz (bkz. api/maa/[...yol])
      const resp = await fetch('/api/maa/portfolio-signal/adaptive_rotation')
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
      // Sunucu tarafi proxy: MAA'nin adresi tarayiciya sizmaz (bkz. api/maa/[...yol])
      const resp = await fetch(`/api/maa/narrative-verified/${ticker.toUpperCase()}`)
      const data = await resp.json()
      if (data.error) {
        setError(data.error)
      } else {
        setResult(data)
      }
      // Gecmis hafiza kayitlarini da ayrica cek (paralel, ana sonucu bekletmeden)
      fetch(`/api/maa/memory/${ticker.toUpperCase()}`)
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
    setAranmisTicker(ticker.toUpperCase())
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

      <PiyasaSinyalleri ticker={aranmisTicker} />
      <BistArastirmaMasasi />
      <RaporlarKarti />
    </div>
  )
}
