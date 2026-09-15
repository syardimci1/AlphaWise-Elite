// Koyfin olay katmani - Olay Semasi (contracts/C1_olay_semasi.md).
//
// Bu dosya 4 kaynagin HAM API yanitlarini C1.KoyfinOlay'a cevirir.
// Alan eslemeleri contracts/kaynak_haritasi.md'de belgelenmis, canli
// ornek veriyle dogrulanmistir - burada TEKRAR ACIKLANMAZ, yalnizca
// uygulanir.
import { gunStringindenUtcMs } from './koyfin-zaman'

export type KoyfinOlayTipi = '13F' | 'DARK_POOL' | 'CONGRESS' | 'INSIDER'

export interface KoyfinOlay {
  id: string
  tip: KoyfinOlayTipi
  symbol: string
  ts_utc: number
  kaynak: string
  ozet: string
  detay_url: string | null
  ham_veri_ref: Record<string, unknown>
  confidence: number
  kaynak_zamani_utc: number
}

/** Gecersiz sema dayanikliligi (FAZ 4 test 11): tek bir bozuk kayit (orn.
 * eksik/bozuk tarih alani) map() icinde firlatirsa TUM diziyi goturur.
 * Bu yardimci HER kaydi ayri ayri dener; basarisiz olan DUSURULUR ve
 * console.warn ile ORNEGIYLE loglanir (sessiz yutma YOK) - digerleri
 * ETKILENMEZ. */
function guvenliMap<T>(kaynakAdi: string, kayitlar: T[], donustur: (k: T) => KoyfinOlay): KoyfinOlay[] {
  const sonuc: KoyfinOlay[] = []
  for (const kayit of kayitlar) {
    try {
      sonuc.push(donustur(kayit))
    } catch (e) {
      console.warn(`[koyfin] ${kaynakAdi}: gecersiz kayit dusuruldu -`, e, kayit)
    }
  }
  return sonuc
}

/** Deterministik id: ayni girdi HER ZAMAN ayni id'yi uretir (C1: idempotentlik). */
function olayId(...parcalar: (string | number)[]): string {
  const metin = parcalar.join('|')
  let h = 0
  for (let i = 0; i < metin.length; i++) {
    h = (h * 31 + metin.charCodeAt(i)) | 0
  }
  return `k${(h >>> 0).toString(36)}`
}

export function congressOlaylari(symbol: string, trades: any[]): KoyfinOlay[] {
  return guvenliMap('CONGRESS', trades || [], (t) => ({
    id: olayId('CONGRESS', symbol, t.transaction_date, t.member, t.transaction_type, t.amount_range),
    tip: 'CONGRESS' as const,
    symbol,
    ts_utc: gunStringindenUtcMs(t.transaction_date),
    kaynak: `congress_trading:${t.source || 'bilinmiyor'}`,
    ozet: `${t.member} (${t.chamber}) ${t.transaction_type} ${t.amount_range}`,
    detay_url: null,
    ham_veri_ref: t,
    confidence: 1.0,
    kaynak_zamani_utc: gunStringindenUtcMs(t.disclosure_date),
  }))
}

export function insiderOlaylari(symbol: string, kayitlar: any[]): KoyfinOlay[] {
  return guvenliMap('INSIDER', kayitlar || [], (k) => ({
    id: olayId('INSIDER', symbol, k.kisi, k.islem_tarihi, k.adet, k.islem_fiyati),
    tip: 'INSIDER' as const,
    symbol,
    ts_utc: gunStringindenUtcMs(k.islem_tarihi),
    kaynak: 'sec_form4_direct',
    ozet: k.acik_piyasa
      ? `${k.kisi}: ${k.acik_piyasa_yonu} ${k.adet} adet @ $${k.islem_fiyati}`
      : `${k.kisi}: ${k.islem_turu_ham} (${k.adet} adet)`,
    detay_url: null,
    ham_veri_ref: k,
    confidence: k.acik_piyasa ? 1.0 : 0.6, // V-004: acik piyasa disi (hibe/odul) daha dusuk tamlik
    kaynak_zamani_utc: gunStringindenUtcMs(k.dosyalama_tarihi),
  }))
}

/** V-001: gunluk kisa hacim orani, 10-gunluk trailing ortalamanin +ESIK puan
 * uzerindeyse olay uretilir. Her gun icin degil - aksi halde grafik
 * kalabalisir (FAZ 3 gorsel-gurultu testi). */
const DARK_POOL_ESIK_PUAN = 10

export function darkPoolOlaylari(symbol: string, regshoYaniti: any): KoyfinOlay[] {
  const gunler: any[] = regshoYaniti?.gunler || []
  const ortalama: number = regshoYaniti?.ortalama_kisa_hacim_orani_yuzde ?? 0
  const esikUstu = gunler.filter((g) => (g?.kisa_hacim_orani_yuzde ?? -Infinity) - ortalama >= DARK_POOL_ESIK_PUAN)
  return guvenliMap('DARK_POOL', esikUstu, (g) => ({
      id: olayId('DARK_POOL', symbol, g.tarih),
      tip: 'DARK_POOL' as const,
      symbol,
      ts_utc: gunStringindenUtcMs(g.tarih),
      kaynak: 'finra_regsho',
      ozet: `Kisa hacim orani %${g.kisa_hacim_orani_yuzde.toFixed(1)} (10g ort. %${ortalama.toFixed(1)})`,
      detay_url: null,
      ham_veri_ref: g,
      confidence: 1.0,
      kaynak_zamani_utc: gunStringindenUtcMs(g.tarih), // V-007/kaynak_haritasi: ayri yayin-gecikme alani yok
    }))
}

/** Idempotentlik (C1): ayni id'li olay birden fazla kez gelirse (ayni
 * kaynagin iki kez cekilmesi, onbellek+canli cakismasi vb.) TEK kopya
 * kalir. markerlariKumele() bunun YERINE GECMEZ - o gun-bazli GORSEL
 * kumelemedir, bu ise KIMLIK-bazli dedup'tir; ikisi farkli sorunlar
 * cozer ve bu yuzden AYRI adimlardir (once tekillestir, sonra kumele). */
export function olaylariTekillestir(olaylar: KoyfinOlay[]): KoyfinOlay[] {
  const gorulen = new Map<string, KoyfinOlay>()
  for (const o of olaylar) {
    if (!gorulen.has(o.id)) gorulen.set(o.id, o)
  }
  return [...gorulen.values()]
}

export function onucFOlaylari(symbol: string, sahipler: any[]): KoyfinOlay[] {
  return guvenliMap('13F', sahipler || [], (s) => ({
    id: olayId('13F', symbol, s.kurum_cik, s.accession),
    tip: '13F' as const,
    symbol,
    ts_utc: gunStringindenUtcMs(s.donem), // gercek olay: pozisyonun ait oldugu donem sonu
    kaynak: 'sec_edgar_13f_direct',
    ozet: `${s.kurum} ${s.donem} donemi icin $${Number(s.hisse_pozisyonu?.deger_usd || 0).toLocaleString('tr-TR')} pozisyon bildirdi`,
    detay_url: `https://www.sec.gov/Archives/edgar/data/${s.kurum_cik}/${String(s.accession).replace(/-/g, '')}/`,
    ham_veri_ref: s,
    confidence: s.cusip_dogrulandi ? 1.0 : 0.7, // V-005
    kaynak_zamani_utc: gunStringindenUtcMs(s.dosyalama_tarihi),
  }))
}
