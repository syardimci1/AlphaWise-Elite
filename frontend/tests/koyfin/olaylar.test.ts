// Kategoriler: OLAY NORMALLESTIRME (C1), IKI-ZAMANLI ALAN AYRIMI,
// CONFIDENCE KURALLARI, BOS/GECERSIZ VERI DAYANIKLILIGI, IDEMPOTENTLIK,
// DARK POOL ESIK FILTRESI (V-001), 13F DETAY_URL INSASI (V-003 kismi).
//
// Fixture'lar contracts/kaynak_haritasi.md'deki GERCEK canli ornek
// verilerdir (14-15.09.2026, NVDA) - uydurulmamistir.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  congressOlaylari, insiderOlaylari, darkPoolOlaylari, onucFOlaylari,
  olaylariTekillestir,
} from '../../src/lib/koyfin-olaylar'
import { gunStringindenUtcMs } from '../../src/lib/koyfin-zaman'

const GERCEK_CONGRESS = {
  member: 'Gilbert Cisneros', chamber: 'House', ticker: 'NVDA',
  transaction_type: 'Sale', transaction_date: '2026-08-18',
  disclosure_date: '2026-09-11', amount_range: '$1,001 - $15,000', source: 'fmp',
}

const GERCEK_INSIDER_ACIK_PIYASA = {
  islem_tarihi: '2026-09-03', dosyalama_tarihi: '2026-09-08',
  kisi: 'STEVENS MARK A', islem_turu_ham: 'Open market or private sale',
  acik_piyasa: true, acik_piyasa_yonu: 'satis', adet: 198707.0, islem_fiyati: 227.6954,
}

const GERCEK_INSIDER_HIBE = {
  islem_tarihi: '2026-09-09', dosyalama_tarihi: '2026-09-11',
  kisi: 'Parker Nicholas P.', islem_turu_ham: 'Grant, award or other acquisition pursuant to Rule 16b-3(d)',
  acik_piyasa: false, acik_piyasa_yonu: null, adet: 172507.0, islem_fiyati: 0.0,
}

const GERCEK_13F = {
  kurum: 'BlackRock, Inc.', kurum_cik: '2012383', donem: '2026-06-30',
  dosyalama_tarihi: '2026-08-07', accession: '0002012383-26-003238',
  cusip_dogrulandi: true, hisse_pozisyonu: { deger_usd: 226560080545, adet: 607367113 },
}

const GERCEK_REGSHO = {
  ortalama_kisa_hacim_orani_yuzde: 39.37,
  gunler: [
    { tarih: '2026-09-14', kisa_hacim_orani_yuzde: 44.04, kisa_hacim: 1, kisa_muaf_hacim: 1, toplam_hacim: 1 }, // +4.67 -> ESIK ALTI
    { tarih: '2026-09-11', kisa_hacim_orani_yuzde: 55.0, kisa_hacim: 1, kisa_muaf_hacim: 1, toplam_hacim: 1 },  // +15.63 -> ESIK USTU
  ],
}

test('OLAY/CONGRESS: iki-zamanli alanlar dogru ayrisir (islem != aciklama)', () => {
  const [olay] = congressOlaylari('NVDA', [GERCEK_CONGRESS])
  assert.equal(olay.ts_utc, gunStringindenUtcMs('2026-08-18'))
  assert.equal(olay.kaynak_zamani_utc, gunStringindenUtcMs('2026-09-11'))
  assert.notEqual(olay.ts_utc, olay.kaynak_zamani_utc)
  assert.equal(olay.kaynak, 'congress_trading:fmp')
  assert.equal(olay.confidence, 1.0)
})

test('OLAY/INSIDER: acik piyasa disi (hibe) kaydi dusuk confidence alir (V-004)', () => {
  const [acik] = insiderOlaylari('NVDA', [GERCEK_INSIDER_ACIK_PIYASA])
  const [hibe] = insiderOlaylari('NVDA', [GERCEK_INSIDER_HIBE])
  assert.equal(acik.confidence, 1.0)
  assert.equal(hibe.confidence, 0.6)
  assert.match(acik.ozet, /satis/)
  assert.match(hibe.ozet, /Grant/)
})

test('OLAY/13F: detay_url CIK+accession\'dan dogru insa edilir, yeni API cagrisi gerekmez', () => {
  const [olay] = onucFOlaylari('NVDA', [GERCEK_13F])
  assert.equal(olay.detay_url, 'https://www.sec.gov/Archives/edgar/data/2012383/000201238326003238/')
  assert.equal(olay.ts_utc, gunStringindenUtcMs('2026-06-30')) // donem = gercek olay tarihi
  assert.equal(olay.kaynak_zamani_utc, gunStringindenUtcMs('2026-08-07')) // dosyalama = aciklama
})

test('OLAY/13F: cusip dogrulanmamissa confidence duser (V-005)', () => {
  const [olay] = onucFOlaylari('NVDA', [{ ...GERCEK_13F, cusip_dogrulandi: false }])
  assert.equal(olay.confidence, 0.7)
})

test('OLAY/DARK_POOL: V-001 esigi - yalnizca +10 puan ustundeki gun olay uretir', () => {
  const olaylar = darkPoolOlaylari('NVDA', GERCEK_REGSHO)
  assert.equal(olaylar.length, 1)
  assert.equal(olaylar[0].ts_utc, gunStringindenUtcMs('2026-09-11'))
})

test('OLAY/BOS-VERI: 4 normalize fonksiyonu da null/undefined/bos girdiyle COKMEZ', () => {
  assert.deepEqual(congressOlaylari('NVDA', []), [])
  assert.deepEqual(congressOlaylari('NVDA', undefined as any), [])
  assert.deepEqual(insiderOlaylari('NVDA', null as any), [])
  assert.deepEqual(onucFOlaylari('NVDA', []), [])
  assert.deepEqual(darkPoolOlaylari('NVDA', null), [])
  assert.deepEqual(darkPoolOlaylari('NVDA', {}), [])
})

test('OLAY/IDEMPOTENTLIK: ayni girdi ayni id uretir, tekillestirme tek kopya birakir', () => {
  const [a] = congressOlaylari('NVDA', [GERCEK_CONGRESS])
  const [b] = congressOlaylari('NVDA', [GERCEK_CONGRESS]) // ayni kaynak IKINCI kez cekilmis gibi
  assert.equal(a.id, b.id)
  const tekil = olaylariTekillestir([a, b])
  assert.equal(tekil.length, 1)
})

test('OLAY/GECERSIZ-SEMA: bozuk TEK kayit dusurulur, AYNI parti icindeki GECERLI kayitlar etkilenmez', () => {
  const gecerli = { ...GERCEK_CONGRESS }
  const bozuk = { member: 'Biri', chamber: 'House', ticker: 'NVDA', transaction_type: 'Sale', /* transaction_date EKSIK -> gunStringindenUtcMs firlatir */ disclosure_date: '2026-09-11', amount_range: '$1' }
  const orijinalWarn = console.warn
  let uyariGeldiMi = false
  console.warn = () => { uyariGeldiMi = true }
  const sonuc = congressOlaylari('NVDA', [gecerli, bozuk as any])
  console.warn = orijinalWarn
  assert.equal(sonuc.length, 1) // yalnizca gecerli olan hayatta kaldi
  assert.ok(sonuc[0].ozet.includes('Cisneros'))
  assert.equal(uyariGeldiMi, true) // sessiz yutma YOK - loglandi
})

test('OLAY/FARKLI-OLAY-AYNI-GUN: farkli iki olay YANLISLIKLA tekillesmez', () => {
  const congressOlay = congressOlaylari('NVDA', [GERCEK_CONGRESS])[0]
  const insiderOlay = insiderOlaylari('NVDA', [GERCEK_INSIDER_HIBE])[0]
  const sonuc = olaylariTekillestir([congressOlay, insiderOlay])
  assert.equal(sonuc.length, 2) // farkli id'ler - ikisi de korunmali
})
