'use client'
/**
 * Bildirim merkezi (Madde 28).
 *
 * Sistemde alarm URETIMI vardi ama GORUNURLUGU yoktu: uc ayri bicimde, dort
 * ayri dosyada birikiyordu ve kimse bakmadikca hicbir yerde gorunmuyordu.
 *
 * BU BILESENIN DEGISMEZ KURALI
 * ============================
 * "Alarm yok" yazisi YALNIZCA tum kaynaklar okunabildiginde cikar. Bir kaynak
 * okunamadiysa liste bos olsa bile bunu ACIKCA soyler. Karar mantigi
 * src/lib/bildirim-ozet.js icinde saf ve TESTLIDIR (9 test).
 */
import { useEffect, useState } from 'react'
import { durumOzeti, rozetSayisi, duzeyRengi, kaynakEtiketi }
  from '@/lib/bildirim-ozet.js'

const RENK = { yuzey: '#1e293b', cizgi: '#334155', vurgu: '#D4AF37',
               metin: '#e2e8f0', ikincil: '#94a3b8', soluk: '#64748b' }

export default function BildirimMerkezi() {
  const [veri, setVeri] = useState<any>(null)
  const [hata, setHata] = useState('')
  const [acik, setAcik] = useState(false)

  useEffect(() => {
    let iptal = false
    fetch('/api/bildirimler')
      .then((r) => r.json())
      .then((d) => { if (!iptal) { d?.hata ? setHata(d.hata) : setVeri(d) } })
      .catch((e) => { if (!iptal) setHata('Bildirim servisine ulasilamiyor: ' + e.message) })
    return () => { iptal = true }
  }, [])

  // Hata durumunda da SESSIZ KALINMAZ: durumOzeti(null) uyarici metin uretir.
  const ozet = hata ? null : veri?.ozet
  const durum = durumOzeti(ozet)
  const rozet = rozetSayisi(ozet)

  return (
    <div style={{ background: RENK.yuzey, border: `1px solid ${durum.vurgulu ? durum.renk : RENK.cizgi}`,
                  borderRadius: 8, padding: 14, marginTop: 24 }}>
      <button onClick={() => setAcik(!acik)}
        style={{ all: 'unset', cursor: 'pointer', display: 'flex', width: '100%',
                 alignItems: 'center', gap: 10, flexWrap: 'wrap', minHeight: 40 }}>
        <span style={{ color: RENK.vurgu, fontWeight: 'bold', fontSize: 15 }}>
          Bildirim Merkezi
        </span>
        {rozet > 0 && (
          <span style={{ background: durum.renk, color: '#0f172a', fontSize: 11,
                         fontWeight: 'bold', borderRadius: 10, padding: '1px 8px' }}>
            {rozet}
          </span>
        )}
        <span style={{ color: durum.renk, fontSize: 12, flex: '1 1 auto', minWidth: 0 }}>
          {durum.metin}
        </span>
        <span style={{ color: RENK.soluk, fontSize: 11 }}>{acik ? 'gizle' : 'göster'}</span>
      </button>

      {acik && (
        <div style={{ marginTop: 12 }}>
          <div style={{ color: RENK.ikincil, fontSize: 11, marginBottom: 8 }}>
            Kaynaklar
          </div>
          {(veri?.kaynak_durumlari || []).map((k: any) => {
            const e = kaynakEtiketi(k.durum)
            return (
              <div key={k.kaynak} style={{ display: 'flex', justifyContent: 'space-between',
                                           gap: 8, flexWrap: 'wrap', padding: '3px 0' }}>
                <span style={{ color: RENK.metin, fontSize: 12 }}>{k.ad}</span>
                <span style={{ color: e.renk, fontSize: 11 }}>
                  {e.metin} · {k.olay_sayisi} kayıt
                </span>
              </div>
            )
          })}

          <div style={{ color: RENK.ikincil, fontSize: 11, margin: '12px 0 6px' }}>
            Kayıtlar {veri?.kesilen ? `(${veri.kesilen} tanesi listelenmedi)` : ''}
          </div>
          {(veri?.bildirimler || []).length === 0 && (
            <div style={{ color: RENK.soluk, fontSize: 12 }}>
              Listelenecek kayıt yok.
            </div>
          )}
          {(veri?.bildirimler || []).map((b: any, i: number) => (
            <div key={i} style={{ borderTop: `1px solid ${RENK.cizgi}`, padding: '8px 0' }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                <span style={{ color: duzeyRengi(b.duzey), fontSize: 10,
                               border: `1px solid ${duzeyRengi(b.duzey)}`,
                               borderRadius: 8, padding: '1px 6px' }}>{b.duzey}</span>
                <span style={{ color: RENK.soluk, fontSize: 11 }}>
                  {b.zaman || 'zaman çözülemedi'}
                </span>
                <span style={{ color: RENK.soluk, fontSize: 11 }}>{b.kaynak}</span>
              </div>
              <div style={{ color: RENK.metin, fontSize: 12, marginTop: 4,
                            overflowWrap: 'anywhere' }}>{b.mesaj}</div>
            </div>
          ))}
          {hata && <div style={{ color: '#f87171', fontSize: 12 }}>{hata}</div>}
        </div>
      )}
    </div>
  )
}
