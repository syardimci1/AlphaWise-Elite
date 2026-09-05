'use client'
/**
 * Dashboard'un SAF SUNUM bilesenleri.
 *
 * NEDEN AYRI DOSYA
 * ================
 * Bu bilesenler once dashboard/page.tsx icinde yasiyordu ve oradan disa
 * AKTARILAMIYORLARDI: Next.js App Router bir page dosyasinin `default`
 * disinda bilesen disa aktarmasina IZIN VERMEZ. Denendi ve tsc reddetti:
 *   "Property 'BolgeKarti' is incompatible with index signature ...
 *    not assignable to type 'never'"
 * Yani 1.100 satirlik sayfanin sunum katmani tek basina calistirilamiyordu;
 * dolayisiyla 390px davranisi da OLCULEMIYORDU.
 *
 * Bilesenler buraya AYNEN tasindi (yeniden yazilmadi). Dar ekran icin
 * eklenen her sey gerekcesiyle isaretlidir.
 */
import React from 'react'

const BOLGE_BASLIKLARI: Record<string, string> = {
  giris_bolgesi: 'Giris Bolgesi',
  ekleme_bolgesi: 'Ekleme Bolgesi',
  kademeli_kar_realizasyonu: 'Kademeli Kar Realizasyonu',
  teknik_seviyeler: 'Teknik Seviyeler',
}
export function BolgeKarti({ bolgeAdi, deger }: { bolgeAdi: string; deger: any }) {
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

export type SinyalDurumu = 'yukleniyor' | 'veri' | 'hata'

export function DurumRozeti({ metin, renk }: { metin: string; renk: string }) {
  return (
    <span style={{
      fontSize: 10, padding: '2px 8px', borderRadius: 10, whiteSpace: 'nowrap',
      border: `1px solid ${renk}`, color: renk, marginLeft: 8,
    }}>
      {metin}
    </span>
  )
}

export function SinyalKutusu({
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

export function Satir({ etiket, deger }: { etiket: string; deger: React.ReactNode }) {
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

// Ust bar — 390px'te tasmamasi icin AYRI bir bilesen.
// OLCULDU: baslik + e-posta + cikis dugmesi tek satirda ~400px yer istiyor,
// oysa 390px ekranda kok dolgusundan sonra ~326px kaliyordu ve satir
// SARMIYORDU (flexWrap yoktu). Artik sariyor ve e-posta uzun oldugunda
// kirpiliyor.
export function UstBar({ userEmail, onCikis }: { userEmail: string; onCikis: () => void }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      marginBottom: 32, flexWrap: 'wrap', gap: 8,
    }}>
      <h1 style={{ color: '#D4AF37', margin: 0, fontSize: 'clamp(20px, 6vw, 32px)' }}>ALPHAWISE</h1>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <span style={{
          fontSize: 14, color: '#94a3b8', minWidth: 0,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{userEmail}</span>
        <button onClick={onCikis} style={{
          background: 'transparent', border: '1px solid #334155', color: '#e2e8f0',
          padding: '8px 14px', borderRadius: 6, cursor: 'pointer',
          flexShrink: 0, minHeight: 40,
        }}>
          Cikis
        </button>
      </div>
    </div>
  )
}

// Arama formu — 390px davranisi olculebilsin diye ayri bilesen.
//
// GORUNUM DEGISTIRILMEDI: renkler, dolgular, kose yaricaplari ve altin
// dolgulu dugme AYNEN korundu. Yalnizca dar ekranda tasmayi onleyen iki sey
// eklendi:
//   1. flexWrap: dar ekranda dugme alt satira gecebilsin.
//   2. minWidth: 0 — girdide ZATEN flex:1 vardi, ama flex ogelerinin
//      varsayilan min-width degeri "auto"dur; yani girdi, yer tutucu metninin
//      ("Hisse kodu girin (orn: NVDA)") ic genisliginin altina INEMEZ ve
//      dugmeyi disari iter. minWidth:0 bu tabani kaldirir.
export function AramaFormu({ ticker, setTicker, loading, onGonder }: any) {
  return (
    <form onSubmit={onGonder} style={{
      display: 'flex', gap: 8, marginBottom: 32, flexWrap: 'wrap',
    }}>
      <input
        type="text" placeholder="Hisse kodu girin (orn: NVDA)" value={ticker}
        onChange={(e: any) => setTicker(e.target.value)}
        style={{ flex: 1, minWidth: 0, padding: 14, borderRadius: 8,
                 border: '1px solid #334155', background: '#1e293b',
                 color: '#e2e8f0', fontSize: 16 }}
      />
      <button type="submit" disabled={loading}
        style={{ padding: '14px 28px', borderRadius: 8, border: 'none',
                 background: '#D4AF37', color: '#0f172a', fontWeight: 'bold',
                 cursor: 'pointer', flexShrink: 0 }}>
        {loading ? 'Analiz ediliyor...' : 'Analiz Et'}
      </button>
    </form>
  )
}

