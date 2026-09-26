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
 * src/lib/bildirim-ozet.js icinde saf ve TESTLIDIR (18 test).
 *
 * YETKISIZ ROL: bu kural ARIZA icindir, YETKISIZLIK icin degildir (22.09.2026).
 * /api/bildirimler 403 donerse (role='user') bu iki durum birbirine
 * KARISTIRILMAZ: bilesen "alarm yok" ya da "bakamadim" demez, TAMAMEN
 * GIZLENIR (null doner). Ayrim erisimYetkisizMi() ile yapilir - yalnizca
 * 403'u yakalar, 500/502/504 gibi gercek arizalari DEGIL (bkz. o
 * fonksiyonun testleri: bir servis cokusu "yetkisiz" ile karismamali).
 *
 * DENETIM EKLENTILERI (26.09.2026, bildirim merkezi denetimi)
 * =============================================================
 * FAZ 0/1'de uc dogrulanmis boslugun kapatilmasi: (1) otomatik yenileme HIC
 * yoktu -> 30sn polling eklendi (ADR-001, kanit/faz0-6 belgeleri). (2) bildirim
 * bazli okundu/okunmadi kalicilik hic yoktu, rozet hep TOPLAM kritik+alarm
 * sayisini gosteriyordu -> src/lib/bildirim-okundu.js (ADR-004). (3) klavye/
 * ARIA erisilebilirligi sifirdi -> ADR-005.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { durumOzeti, rozetSayisi, duzeyRengi, kaynakEtiketi, bayatlikMetni, erisimYetkisizMi }
  from '@/lib/bildirim-ozet.js'
import { bildirimIdUret, okunanlariOku, okunduIsaretle, okunmamisSayi, okunanAnahtari }
  from '@/lib/bildirim-okundu.js'

const RENK = { yuzey: '#1e293b', cizgi: '#334155', vurgu: '#D4AF37',
               metin: '#e2e8f0', ikincil: '#94a3b8', soluk: '#64748b' }

// ADR-001: FAZ 1'de dogrulandi - onceden HIC otomatik yenileme yoktu, kullanici
// sayfayi elle yenilemeden yeni alarm gormuyordu. WebSocket Y2 geregi (yeni
// bagimlilik/sunucu bileseni) reddedildi; 30sn native setInterval + fetch.
const YENILEME_MS = 30_000

export default function BildirimMerkezi() {
  const [veri, setVeri] = useState<any>(null)
  const [hata, setHata] = useState('')
  const [acik, setAcik] = useState(false)
  const [gizli, setGizli] = useState(false)
  const [kullaniciId, setKullaniciId] = useState<string | null>(null)
  const [okunanlar, setOkunanlar] = useState<Set<string>>(new Set())
  const denetleyiciRef = useRef<AbortController | null>(null)

  const yukle = useCallback(() => {
    denetleyiciRef.current?.abort()
    const denetleyici = new AbortController()
    denetleyiciRef.current = denetleyici
    fetch('/api/bildirimler', { signal: denetleyici.signal })
      .then(async (r) => {
        // Yetkisiz (403): bilesen ariza mesaji GOSTERMEZ, tamamen gizlenir.
        // Once burada kontrol edilir ki govde parse edilip bos/hatali
        // sanilmasin - HTTP durumu tek dogruluk kaynagidir.
        if (erisimYetkisizMi(r.status)) { setGizli(true); return }
        const d = await r.json()
        if (d?.hata) setHata(d.hata)
        else { setVeri(d); setHata('') }
      })
      .catch((e) => { if (e?.name !== 'AbortError') setHata('Bildirim servisine ulasilamiyor: ' + e.message) })
  }, [])

  useEffect(() => {
    yukle()
    const zamanlayici = setInterval(yukle, YENILEME_MS)
    return () => { clearInterval(zamanlayici); denetleyiciRef.current?.abort() }
  }, [yukle])

  // ADR-004: okundu/okunmadi kalicilik kullanicinin KENDI kimligini gerektirir
  // (ad alani olmadan bir kullanicinin "okundu" durumu baskasina karisir).
  // /api/config/kimlik zaten grafik terminali/gosterge-kalicilik icin var olan
  // ayni uc. Kimlik alinamazsa ozellik FAIL-CLOSED devre disi kalir - bu bir
  // guvenlik siniri degil (icerik zaten kullaniciya ozel degil, bkz. route.ts
  // yorumu), sadece yanlis ad alanina yazmamak icindir; rozet bu durumda eski
  // TOPLAM davranisina (rozetSayisi) duser.
  useEffect(() => {
    let iptal = false
    fetch('/api/config/kimlik')
      .then(async (r) => (r.ok ? r.json() : null))
      .then((d) => { if (!iptal && d?.kullaniciId) setKullaniciId(d.kullaniciId) })
      .catch(() => {})
    return () => { iptal = true }
  }, [])

  useEffect(() => {
    if (!kullaniciId || typeof window === 'undefined') return
    setOkunanlar(okunanlariOku(window.localStorage, kullaniciId))
    // Iki sekme senkronizasyonu: tarayici 'storage' olayini SADECE DIGER
    // sekmelerde otomatik ateşler (kendi sekmemizde setItem sonrasi
    // asagidaki isaretle() zaten state'i dogrudan gunceller).
    const anahtar = okunanAnahtari(kullaniciId)
    const dinle = (e: StorageEvent) => {
      if (e.key === anahtar) setOkunanlar(okunanlariOku(window.localStorage, kullaniciId))
    }
    window.addEventListener('storage', dinle)
    return () => window.removeEventListener('storage', dinle)
  }, [kullaniciId])

  const isaretle = useCallback((id: string) => {
    if (!kullaniciId || typeof window === 'undefined') return
    okunduIsaretle(window.localStorage, kullaniciId, id)
    setOkunanlar(okunanlariOku(window.localStorage, kullaniciId))
  }, [kullaniciId])

  // Yetkisiz roldeyse bilesen hic render edilmez (Hook'lardan SONRA -
  // React kurali: erken donus, hook sirasini bozmamak icin her zaman
  // ayni sayida Hook cagrildiktan sonra gelmelidir).
  if (gizli) return null

  // Hata durumunda da SESSIZ KALINMAZ: durumOzeti(null) uyarici metin uretir.
  const ozet = hata ? null : veri?.ozet
  const durum = durumOzeti(ozet)
  const bildirimler = veri?.bildirimler || []
  // ADR-004: kimlik biliniyorsa gercek OKUNMAMIS sayisi (panoyu acip bakinca
  // sifira doner); bilinmiyorsa eski TOPLAM davranisina fail-closed duser.
  const rozet = kullaniciId ? okunmamisSayi(bildirimler, okunanlar) : rozetSayisi(ozet)

  return (
    <div style={{ background: RENK.yuzey, border: `1px solid ${durum.vurgulu ? durum.renk : RENK.cizgi}`,
                  borderRadius: 8, padding: 14, marginTop: 24 }}>
      <button
        aria-label="Bildirim merkezini ac/kapat"
        aria-expanded={acik}
        aria-controls="bildirim-paneli"
        onClick={() => setAcik(!acik)}
        onKeyDown={(e) => { if (e.key === 'Escape') setAcik(false) }}
        style={{ all: 'unset', cursor: 'pointer', display: 'flex', width: '100%',
                 alignItems: 'center', gap: 10, flexWrap: 'wrap', minHeight: 40 }}>
        <span style={{ color: RENK.vurgu, fontWeight: 'bold', fontSize: 15 }}>
          Bildirim Merkezi
        </span>
        {rozet > 0 && (
          <span aria-label={`${rozet} okunmamis onemli kayit`}
                style={{ background: durum.renk, color: '#0f172a', fontSize: 11,
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
        <div id="bildirim-paneli" role="region" aria-label="Bildirim listesi"
             onKeyDown={(e) => { if (e.key === 'Escape') setAcik(false) }}
             style={{ marginTop: 12 }}>
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
          {bildirimler.length === 0 && (
            <div style={{ color: RENK.soluk, fontSize: 12 }}>
              Listelenecek kayıt yok.
            </div>
          )}
          {bildirimler.map((b: any, i: number) => {
            const id = bildirimIdUret(b)
            const okunduMu = kullaniciId ? okunanlar.has(id) : false
            const tiklanabilir = Boolean(kullaniciId)
            return (
              <div key={i}
                   role={tiklanabilir ? 'button' : undefined}
                   tabIndex={tiklanabilir ? 0 : undefined}
                   aria-pressed={tiklanabilir ? okunduMu : undefined}
                   aria-label={tiklanabilir
                     ? (okunduMu ? 'Okundu isaretli kayit' : 'Okunmadi - okundu isaretlemek icin Enter')
                     : undefined}
                   onClick={tiklanabilir ? () => isaretle(id) : undefined}
                   onKeyDown={tiklanabilir ? (e) => {
                     if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); isaretle(id) }
                   } : undefined}
                   style={{ borderTop: `1px solid ${RENK.cizgi}`, padding: '8px 0',
                            cursor: tiklanabilir ? 'pointer' : 'default',
                            opacity: okunduMu ? 0.55 : 1 }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
                  {tiklanabilir && !okunduMu && (
                    <span aria-hidden="true" style={{ color: RENK.vurgu, fontSize: 10 }}>●</span>
                  )}
                  <span style={{ color: duzeyRengi(b.duzey), fontSize: 10,
                                 border: `1px solid ${duzeyRengi(b.duzey)}`,
                                 borderRadius: 8, padding: '1px 6px' }}>{b.duzey}</span>
                  <span style={{ color: RENK.soluk, fontSize: 11 }}>
                    {b.zaman || 'zaman çözülemedi'}
                  </span>
                  <span style={{ color: RENK.soluk, fontSize: 11 }}>{b.kaynak}</span>
                </div>
                {/* Bayatlik: bir hafta once kapanmis bir sorunun ACIK gibi
                    gorunmesini engeller. Kayit SILINMEZ, yalnizca olgu yazilir. */}
                {(() => {
                  const y = bayatlikMetni(b)
                  if (!y) return null
                  return (
                    <div style={{ color: y.kapanmis ? '#4ade80' : RENK.soluk,
                                  fontSize: 11, marginTop: 2 }}>
                      {y.metin}
                      {y.kapanmis ? ' (büyük olasılıkla kapandı)' : ''}
                    </div>
                  )
                })()}
                <div style={{ color: RENK.metin, fontSize: 12, marginTop: 4,
                              overflowWrap: 'anywhere' }}>{b.mesaj}</div>
              </div>
            )
          })}
          {hata && <div role="alert" style={{ color: '#f87171', fontSize: 12 }}>{hata}</div>}
        </div>
      )}
    </div>
  )
}
