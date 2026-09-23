// Kategori: KALICILIK (C3 / ADR-2) - localStorage ad alani, surum gocu, fail-loud hata.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  anahtarUret,
  kaydet,
  yukle,
  sil,
  type Cizim,
  type Depo,
} from '../../src/lib/grafik/cizim-kalicilik'
import { gecerliCizim } from '../../src/lib/grafik/cizim-model'

/** Bellek ici sahte depo - gercek localStorage semantigi (yoksa null doner). */
class BellekDepo implements Depo {
  readonly kutu = new Map<string, string>()
  getItem(anahtar: string): string | null {
    const deger = this.kutu.get(anahtar)
    return deger === undefined ? null : deger
  }
  setItem(anahtar: string, deger: string): void {
    this.kutu.set(anahtar, deger)
  }
  removeItem(anahtar: string): void {
    this.kutu.delete(anahtar)
  }
}

/** Kota dolu tarayici: setItem QuotaExceededError firlatir. */
class KotaDoluDepo extends BellekDepo {
  override setItem(): void {
    const hata = new Error('depolama kotasi doldu')
    hata.name = 'QuotaExceededError'
    throw hata
  }
}

/** Gizli sekme / depolama kapali: okuma bile firlatir. */
class OkunamayanDepo extends BellekDepo {
  override getItem(): string | null {
    throw new Error('SecurityError: depolama erisimi engellendi')
  }
}

const ORNEK_CIZIMLER: Cizim[] = [
  {
    v: 1,
    id: 'c1',
    tip: 'trend',
    noktalar: [
      { t_utc: 1750000000000, fiyat: 390.69 },
      { t_utc: 1750086400000, fiyat: 396.84 },
    ],
    stil: { renk: '#e63946', kalinlik: 2 },
    olusturma_utc: 1750086400001,
  },
  {
    v: 1,
    id: 'c2',
    tip: 'yatay',
    noktalar: [{ t_utc: 1750000000000, fiyat: 400 }],
    stil: { renk: '#457b9d', kalinlik: 1 },
    olusturma_utc: 1750086400002,
  },
]

test('KALICILIK: ornek cizimler cizim-model semasina gercekten uyar (otorite tek)', () => {
  // Bu kilit olmazsa model semasi degistiginde kalicilik testleri kendi
  // uydurdugu bicimle yesil kalir, uretimde her cizim atlanir.
  for (const cizim of ORNEK_CIZIMLER) assert.equal(gecerliCizim(cizim), true)
})

test('KALICILIK: anahtar bicimi ADR-2 ile ayni ve sembol BUYUK harfe normalize edilir', () => {
  assert.equal(anahtarUret('kullanici-7', 'aapl'), 'alphawise:grafik:cizim:v1:kullanici-7:AAPL')
  assert.equal(anahtarUret('kullanici-7', '  tsla  '), 'alphawise:grafik:cizim:v1:kullanici-7:TSLA')
})

test('KALICILIK: bos/undefined kimlik anonim AYRI ad alanina duser', () => {
  assert.equal(anahtarUret('', 'AAPL'), 'alphawise:grafik:cizim:v1:anonim:AAPL')
  assert.equal(anahtarUret(undefined, 'AAPL'), 'alphawise:grafik:cizim:v1:anonim:AAPL')
  assert.notEqual(anahtarUret('', 'AAPL'), anahtarUret('ali', 'AAPL'))
})

test("KALICILIK: sembol normalizasyonu yerelden bagimsiz ('isctr' -> 'ISCTR', 'İ' degil)", () => {
  assert.equal(anahtarUret('ali', 'isctr'), 'alphawise:grafik:cizim:v1:ali:ISCTR')
})

test('KALICILIK: kimlikteki ayrac karakteri kacislanir - ad alani cakismasi YOK', () => {
  // Kacislama olmasa "a" + "B:C" ile "a:B" + "C" ayni anahtari uretirdi (sizinti).
  assert.notEqual(anahtarUret('a', 'B:C'), anahtarUret('a:B', 'C'))
})

test('KALICILIK: normal tur - kaydet/yukle gidis-donusu kayipsiz, uyari yok', () => {
  const depo = new BellekDepo()
  const sonuc = kaydet(depo, 'ali', 'AAPL', ORNEK_CIZIMLER)
  assert.equal(sonuc.basarili, true)
  assert.equal(sonuc.hata, undefined)

  const yuklenen = yukle(depo, 'ali', 'AAPL')
  assert.equal(yuklenen.uyari, undefined)
  assert.deepEqual(yuklenen.cizimler, ORNEK_CIZIMLER)
})

test('KALICILIK: anahtar yoksa bos liste doner, uyari uretmez', () => {
  const depo = new BellekDepo()
  const sonuc = yukle(depo, 'ali', 'MSFT')
  assert.deepEqual(sonuc.cizimler, [])
  assert.equal(sonuc.uyari, undefined)
})

test('KALICILIK: bozuk JSON sessizce yutulmaz - bos liste + gorunur uyari', () => {
  const depo = new BellekDepo()
  depo.setItem(anahtarUret('ali', 'AAPL'), '{bu gecerli json degil')
  const sonuc = yukle(depo, 'ali', 'AAPL')
  assert.deepEqual(sonuc.cizimler, [])
  assert.equal(sonuc.uyari, 'bozuk kayit sifirlandi')
})

test('KALICILIK: bilinmeyen (ileri) surum goc edilemez -> sifirlama + uyari', () => {
  const depo = new BellekDepo()
  depo.setItem(anahtarUret('ali', 'AAPL'), JSON.stringify({ v: 99, cizimler: ORNEK_CIZIMLER }))
  const sonuc = yukle(depo, 'ali', 'AAPL')
  assert.deepEqual(sonuc.cizimler, [])
  assert.match(String(sonuc.uyari), /bilinmeyen surum \(v=99\)/)
})

test('KALICILIK: zarfsiz eski kayit (v0 duz dizi) goc edilir, gocun kendisi uyarida gorunur', () => {
  const depo = new BellekDepo()
  depo.setItem(anahtarUret('ali', 'AAPL'), JSON.stringify(ORNEK_CIZIMLER))
  const sonuc = yukle(depo, 'ali', 'AAPL')
  assert.deepEqual(sonuc.cizimler, ORNEK_CIZIMLER)
  assert.match(String(sonuc.uyari), /v0/)
})

test('KALICILIK: semaya uymayan cizimler atlanir ve KAC tanesi atlandigi uyarida yazar', () => {
  const depo = new BellekDepo()
  const gecerli = ORNEK_CIZIMLER[0]
  const karisik: unknown[] = [
    gecerli,
    { v: 1, id: 'c9', tip: 'ucgen', noktalar: [{ t_utc: 1, fiyat: 2 }], stil: { renk: '#fff', kalinlik: 1 }, olusturma_utc: 1 }, // tanimsiz tip
    { v: 1, id: '', tip: 'yatay', noktalar: [{ t_utc: 1, fiyat: 2 }], stil: { renk: '#fff', kalinlik: 1 }, olusturma_utc: 1 }, // bos kimlik
    { v: 1, id: 'c10', tip: 'trend', noktalar: [{ t_utc: 1, fiyat: 2 }], stil: { renk: '#fff', kalinlik: 1 }, olusturma_utc: 1 }, // eksik nokta (trend 2 ister)
    { v: 1, id: 'c11', tip: 'yatay', noktalar: [{ t_utc: 'dun', fiyat: 2 }], stil: { renk: '#fff', kalinlik: 1 }, olusturma_utc: 1 }, // sonlu olmayan zaman
    { v: 2, id: 'c12', tip: 'yatay', noktalar: [{ t_utc: 1, fiyat: 2 }], stil: { renk: '#fff', kalinlik: 1 }, olusturma_utc: 1 }, // cizim surumu bilinmiyor
    null,
  ]
  depo.setItem(anahtarUret('ali', 'AAPL'), JSON.stringify({ v: 1, cizimler: karisik }))
  const sonuc = yukle(depo, 'ali', 'AAPL')
  assert.deepEqual(sonuc.cizimler, [gecerli])
  assert.equal(sonuc.uyari, '6 cizim semaya uymadigi icin atlandi')
})

test('KALICILIK: kota asimi FIRLATMAZ - {basarili:false, hata} doner', () => {
  const depo = new KotaDoluDepo()
  const sonuc = kaydet(depo, 'ali', 'AAPL', ORNEK_CIZIMLER)
  assert.equal(sonuc.basarili, false)
  assert.match(String(sonuc.hata), /QuotaExceededError/)
})

test('KALICILIK: depo okunamiyorsa (gizli sekme) cokme yok, uyari var', () => {
  const depo = new OkunamayanDepo()
  const sonuc = yukle(depo, 'ali', 'AAPL')
  assert.deepEqual(sonuc.cizimler, [])
  assert.match(String(sonuc.uyari), /depo okunamadi/)
})

test('KALICILIK: kullanici ad alani izolasyonu - A-nin cizimi B-ye GORUNMEZ', () => {
  const depo = new BellekDepo() // ayni tarayici, ayni depo, iki kullanici
  kaydet(depo, 'kullanici-A', 'AAPL', ORNEK_CIZIMLER)
  const bSonuc = yukle(depo, 'kullanici-B', 'AAPL')
  assert.deepEqual(bSonuc.cizimler, [])
  assert.equal(bSonuc.uyari, undefined)
  assert.deepEqual(yukle(depo, 'kullanici-A', 'AAPL').cizimler, ORNEK_CIZIMLER)
})

test('KALICILIK: anonim ad alani gercek kullanicidan yalitiktir', () => {
  const depo = new BellekDepo()
  kaydet(depo, '', 'AAPL', ORNEK_CIZIMLER)
  assert.deepEqual(yukle(depo, 'ali', 'AAPL').cizimler, [])
  assert.deepEqual(yukle(depo, undefined, 'AAPL').cizimler, ORNEK_CIZIMLER)
})

test('KALICILIK: sembol buyuk/kucuk harf farki ayni kaydi acar, farkli sembol acmaz', () => {
  const depo = new BellekDepo()
  kaydet(depo, 'ali', 'aapl', ORNEK_CIZIMLER)
  assert.deepEqual(yukle(depo, 'ali', 'AAPL').cizimler, ORNEK_CIZIMLER)
  assert.deepEqual(yukle(depo, 'ali', 'AapL').cizimler, ORNEK_CIZIMLER)
  assert.deepEqual(yukle(depo, 'ali', 'TSLA').cizimler, [])
})

test('KALICILIK: sil kaydi kaldirir, olmayan anahtarda da firlatmaz', () => {
  const depo = new BellekDepo()
  kaydet(depo, 'ali', 'AAPL', ORNEK_CIZIMLER)
  assert.equal(sil(depo, 'ali', 'AAPL').basarili, true)
  assert.deepEqual(yukle(depo, 'ali', 'AAPL').cizimler, [])
  assert.equal(sil(depo, 'ali', 'AAPL').basarili, true) // ikinci kez: hata yok
})

test('KALICILIK: yukle YAN ETKISIZDIR - bozuk kayit depoda oldugu gibi kalir', () => {
  const depo = new BellekDepo()
  const anahtar = anahtarUret('ali', 'AAPL')
  depo.setItem(anahtar, 'bozuk')
  const ilk = yukle(depo, 'ali', 'AAPL')
  assert.equal(depo.getItem(anahtar), 'bozuk')
  // Ayni girdi -> ayni cikti (saflik).
  assert.deepEqual(yukle(depo, 'ali', 'AAPL'), ilk)
})
