'use client'

/**
 * Bes eksenli temel skor gorseli (Madde 23).
 *
 * FORM SECIMI — bilincli ve gerekceli
 * ===================================
 * Verinin isi "tek bir sirketin bes olcutunu ortak 0-100 olceginde
 * karsilastirmak", yani BUYUKLUK karsilastirmasi. Gorsellestirme kilavuzu
 * bu is icin varsayilan olarak CUBUK ve TEK RENKLI (sequential) palet
 * onerir; besgen/radar bicimi alan olarak yaniltabilir (deger iki katina
 * ciktiginda alan dorde katlanir) ve eksen SIRASINA duyarlidir.
 *
 * Bu yuzden IKISI DE cizilir ve her biri kendi isini yapar:
 *   - Besgen: bir bakista sekil/denge izlenimi (istenen "snowflake" bicimi)
 *   - Altindaki satirlar: olcunun DOGRU okundugu yer (cubuk uzunlugu =
 *     buyukluk) ve ayni zamanda erisilebilir tablo gorunumu.
 * Hicbir sayi yalnizca besgenden okunmak zorunda degildir.
 *
 * RENK
 * ====
 * Tek renk (altin #D4AF37) buyuklugu tasir; olculemeyen eksen notr gri.
 * Bu ikili koyu yuzeyde (#1e293b) dogrulandi: kontrast 4/4 >= 3:1, normal
 * gorus ayrimi dE 18.2, renk korlugunde dE 13.1. Ustelik ayrim RENGE
 * BIRAKILMAZ: olculemeyen eksen KESIKLI cizilir, kosesi YOKTUR ve yaninda
 * "veri yok" / "uygulanamaz" YAZAR.
 *
 * EN KRITIK KURAL
 * ===============
 * Olculemeyen eksen SIFIR UZUNLUKTA CIZILMEZ. Geometrinin tamami test
 * edilmis saf modulde (src/lib/pentagon-geometri.js, 18 test, 8 mutasyon).
 */
import {
  eksenNoktalari, poligonKenarlari, halkaYaricaplari, halkaNoktalari,
  etiketKonumu, durumMetni, genelPuanMetni, kapsamMetni, kisaAd,
  OLCULEMEDI, UYGULANAMAZ,
} from '@/lib/pentagon-geometri.js'

const RENK = {
  yuzey: '#1e293b',
  cizgi: '#334155',
  izgara: '#2f3f55',
  vurgu: '#D4AF37',
  notr: '#64748b',
  metin: '#e2e8f0',
  ikincil: '#94a3b8',
  soluk: '#64748b',
}

type Eksen = {
  anahtar: string
  ad: string
  puan: number | null
  durum: string
  ham: number | null
  gerekce: string
  eksik: string[]
  kaynak: string
  aciklama: string
  yayimlanmis: boolean
  ayrinti?: Record<string, any>
}

type Props = {
  veri: {
    ticker: string
    sirket_adi?: string | null
    eksenler: Eksen[]
    genel_puan: number | null
    genel_gerekce: string
    olculebilen_eksen: number
    asgari_eksen: number
    yasal_uyari?: string
  }
}

// Cizim kutusu besgenden bilincli olarak GENIS: 390px'te olculdugunde yan
// eksen etiketleri kart kenarindan TASIYORDU. Genislik/yukseklik ayri
// tutuldu ki yatayda etiket payi olsun, dikeyde bosluk buyumesin.
const EN = 300
const BOY = 210
const MERKEZ = { x: EN / 2, y: BOY / 2 }
const YARICAP = 66

export default function PentagonSkor({ veri }: Props) {
  const eksenler = veri.eksenler || []
  const noktalar = eksenNoktalari(eksenler, MERKEZ, YARICAP)
  const kenarlar = poligonKenarlari(noktalar)
  const halkalar = halkaYaricaplari(YARICAP)
  const kapsam = kapsamMetni(eksenler, veri.asgari_eksen ?? 3)

  return (
    <div style={{
      background: RENK.yuzey, border: `1px solid ${RENK.cizgi}`,
      borderRadius: 8, padding: 16, flex: '1 1 320px', minWidth: 0, maxWidth: 420,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ color: RENK.vurgu, fontWeight: 'bold', fontSize: 15 }}>
          Beş Eksenli Temel Skor
        </span>
        <span style={{ color: RENK.soluk, fontSize: 11 }}>
          {veri.ticker}{veri.sirket_adi ? ` · ${veri.sirket_adi}` : ''}
        </span>
      </div>

      {/* --- Besgen: bir bakista sekil --- */}
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
        <svg viewBox={`0 0 ${EN} ${BOY}`} role="img"
             aria-label={`${veri.ticker} beş eksenli temel skor, ${kapsam.metin}`}
             style={{ width: '100%', maxWidth: EN, height: 'auto' }}>
          {/* izgara halkalari - geri planda kalir */}
          {halkalar.map((h) => (
            <polygon key={h.kademe}
              points={halkaNoktalari(MERKEZ, h.yaricap, eksenler.length || 5)}
              fill="none" stroke={RENK.izgara} strokeWidth={1} />
          ))}

          {/* eksen cubuklari: olculemeyen KESIKLI */}
          {noktalar.map((p) => (
            <line key={`s-${p.anahtar}`} x1={MERKEZ.x} y1={MERKEZ.y} x2={p.uc.x} y2={p.uc.y}
              stroke={p.tepe === null ? RENK.notr : RENK.cizgi} strokeWidth={1}
              strokeDasharray={p.tepe === null ? '3 4' : undefined} />
          ))}

          {/* deger poligonu; atlanan eksen uzerinden gecen kenar KESIKLI */}
          {kenarlar.length > 0 && (
            <>
              <polygon
                points={kenarlar.map((k) => `${k.a.x.toFixed(2)},${k.a.y.toFixed(2)}`).join(' ')}
                fill={RENK.vurgu} fillOpacity={0.16} stroke="none" />
              {kenarlar.map((k, i) => (
                <line key={`k-${i}`} x1={k.a.x} y1={k.a.y} x2={k.b.x} y2={k.b.y}
                  stroke={RENK.vurgu} strokeWidth={2}
                  strokeDasharray={k.atlamaVar ? '4 4' : undefined}
                  strokeOpacity={k.atlamaVar ? 0.55 : 1} />
              ))}
            </>
          )}

          {/* koseler: yalnizca OLCULEN eksenlerde */}
          {noktalar.filter((p) => p.tepe !== null).map((p) => (
            <circle key={`t-${p.anahtar}`} cx={p.tepe!.x} cy={p.tepe!.y} r={4.5}
              fill={RENK.vurgu} stroke={RENK.yuzey} strokeWidth={2} />
          ))}

          {/* olculemeyen eksenin ucunda kucuk bir "yok" isareti */}
          {noktalar.filter((p) => p.tepe === null).map((p) => {
            const o = { x: MERKEZ.x + (p.uc.x - MERKEZ.x) * 0.5,
                        y: MERKEZ.y + (p.uc.y - MERKEZ.y) * 0.5 }
            return (
              <g key={`y-${p.anahtar}`}>
                <circle cx={o.x} cy={o.y} r={5} fill={RENK.yuzey}
                        stroke={RENK.notr} strokeWidth={1} strokeDasharray="2 2" />
                <line x1={o.x - 2.5} y1={o.y} x2={o.x + 2.5} y2={o.y}
                      stroke={RENK.notr} strokeWidth={1.5} />
              </g>
            )
          })}

          {/* merkez: genel puan.
              Alt yazi ("N/5 eksen olculdu") ONCE burada, poligonun ICINDE
              duruyordu ve dolgu uzerinde OKUNMUYORDU (ekran goruntusunde
              olculdu). Grafigin ALTINA tasindi. Sayinin arkasina da yuzey
              renginde bir plaka konuldu ki dolgunun uzerinde net dursun. */}
          <circle cx={MERKEZ.x} cy={MERKEZ.y - 6} r={19}
                  fill={RENK.yuzey} fillOpacity={0.86} />
          <text x={MERKEZ.x} y={MERKEZ.y + 2} textAnchor="middle"
                fill={veri.genel_puan === null ? RENK.ikincil : RENK.metin}
                fontSize={24} fontWeight="bold">
            {genelPuanMetni(veri.genel_puan)}
          </text>

          {/* eksen etiketleri */}
          {noktalar.map((p, i) => {
            const k = etiketKonumu(MERKEZ, YARICAP, i, noktalar.length, 14)
            const olculdu = p.tepe !== null
            return (
              <text key={`e-${p.anahtar}`} x={k.x} y={k.y}
                    textAnchor={k.hiza as any} dominantBaseline="middle"
                    fill={olculdu ? RENK.ikincil : RENK.notr} fontSize={9}>
                {kisaAd(p.ad)}
              </text>
            )
          })}
        </svg>
      </div>
      <div style={{ textAlign: 'center', color: kapsam.yeterli ? RENK.soluk : RENK.notr,
                    fontSize: 11, marginTop: 2 }}>
        {kapsam.metin}
      </div>

      {/* --- Satirlar: olcunun DOGRU okundugu yer + tablo gorunumu --- */}
      <div style={{ marginTop: 10 }}>
        {eksenler.map((e) => {
          const olculdu = typeof e.puan === 'number'
          return (
            <div key={e.anahtar} style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                            gap: 8, alignItems: 'baseline' }}>
                <span style={{ color: RENK.metin, fontSize: 12 }}>
                  {e.ad}
                  {e.yayimlanmis === false && (
                    <span style={{ color: RENK.soluk, fontSize: 10 }}> (AlphaWise bileşimi)</span>
                  )}
                </span>
                <span style={{
                  color: olculdu ? RENK.metin : RENK.notr, fontSize: 12,
                  fontWeight: olculdu ? 'bold' : 'normal', whiteSpace: 'nowrap',
                }}>
                  {durumMetni({ puan: e.puan, durum: e.durum })}
                </span>
              </div>
              {/* cubuk: buyuklugun dogru okundugu yer */}
              <div style={{ height: 6, background: RENK.izgara, borderRadius: 3,
                            marginTop: 4, overflow: 'hidden' }}>
                {olculdu ? (
                  /* OLCULMUS SIFIR gorunur kalmali: %0 genislik, cizilmemis
                     bir cubuktan ayirt edilemezdi. Taban 3px'lik bir isaret
                     "olculdu ve sifir" oldugunu gosterir. */
                  <div style={{
                    width: `max(3px, ${Math.max(0, Math.min(100, e.puan as number))}%)`,
                    height: '100%', background: RENK.vurgu, borderRadius: 3 }} />
                ) : (
                  <div style={{ width: '100%', height: '100%',
                                backgroundImage: `repeating-linear-gradient(45deg, ${RENK.notr} 0 3px, transparent 3px 7px)`,
                                opacity: 0.5 }} />
                )}
              </div>
              <div style={{ color: RENK.soluk, fontSize: 10, marginTop: 3 }}>
                {e.kaynak}
                {!olculdu && e.gerekce ? ` — ${e.gerekce}` : ''}
              </div>
            </div>
          )
        })}
      </div>

      {/* --- Gerekce: genel puan neden var/yok --- */}
      <div style={{ color: RENK.ikincil, fontSize: 11, marginTop: 12,
                    paddingTop: 10, borderTop: `1px solid ${RENK.cizgi}` }}>
        {veri.genel_gerekce}
      </div>

      {/* --- Gosterge: ayrim renge birakilmaz --- */}
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginTop: 8 }}>
        <span style={{ color: RENK.ikincil, fontSize: 10 }}>
          <svg width="14" height="8" style={{ verticalAlign: 'middle' }}>
            <line x1="0" y1="4" x2="14" y2="4" stroke={RENK.vurgu} strokeWidth="2" />
          </svg> ölçüldü
        </span>
        <span style={{ color: RENK.notr, fontSize: 10 }}>
          <svg width="14" height="8" style={{ verticalAlign: 'middle' }}>
            <line x1="0" y1="4" x2="14" y2="4" stroke={RENK.notr} strokeWidth="2" strokeDasharray="3 3" />
          </svg> ölçülemedi / uygulanamaz (sıfır değildir)
        </span>
      </div>
    </div>
  )
}
