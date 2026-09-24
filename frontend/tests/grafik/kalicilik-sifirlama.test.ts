// Kategori: KALICILIK SIFIRLAMA (C6) ve sekmeler arasi degisiklik algisi.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { baskaSekmeDegistirdi, kayitlariSifirla } from '../../src/lib/grafik/kalicilik-sifirlama'
import { anahtarUret, kaydet, type Depo } from '../../src/lib/grafik/cizim-kalicilik'
import { gostergeAnahtari, gostergeleriKaydet } from '../../src/lib/grafik/gosterge-kalicilik'
import { GecikmeliKayit, type Zamanlayici } from '../../src/lib/grafik/gecikmeli-kayit'

class BellekDepo implements Depo {
  readonly kutu = new Map<string, string>()
  getItem(a: string): string | null {
    return this.kutu.get(a) ?? null
  }
  setItem(a: string, d: string): void {
    this.kutu.set(a, d)
  }
  removeItem(a: string): void {
    this.kutu.delete(a)
  }
}

/** Zamanlayici kurulan isleri biriktirir; `hepsiniCalistir` sure dolmus gibi davranir. */
class ElleSaat implements Zamanlayici {
  private readonly isler = new Map<number, () => void>()
  private sayac = 0
  kur(is: () => void): unknown {
    this.sayac += 1
    this.isler.set(this.sayac, is)
    return this.sayac
  }
  iptal(t: unknown): void {
    this.isler.delete(t as number)
  }
  hepsiniCalistir(): void {
    for (const [k, is] of [...this.isler]) {
      this.isler.delete(k)
      is()
    }
  }
}

const CIZIM = {
  v: 1 as const,
  id: 'c1',
  tip: 'yatay' as const,
  noktalar: [{ t_utc: 1750000000000, fiyat: 400 }],
  stil: { renk: '#457b9d', kalinlik: 1 },
  olusturma_utc: 1750086400002,
}

test('SIFIRLAMA (C6): iki anahtar da silinir; baska sembol ve baska kullanici DOKUNULMAZ', () => {
  const depo = new BellekDepo()
  kaydet(depo, 'ali', 'AAPL', [CIZIM])
  gostergeleriKaydet(depo, 'ali', 'AAPL', ['sma20'], 1)
  kaydet(depo, 'ali', 'TSLA', [CIZIM])
  gostergeleriKaydet(depo, 'veli', 'AAPL', ['macd'], 1)

  const sonuc = kayitlariSifirla(depo, new GecikmeliKayit(300, new ElleSaat()), 'ali', 'AAPL')
  assert.deepEqual(sonuc, { basarili: true })
  assert.equal(depo.getItem(anahtarUret('ali', 'AAPL')), null)
  assert.equal(depo.getItem(gostergeAnahtari('ali', 'AAPL')), null)
  assert.notEqual(depo.getItem(anahtarUret('ali', 'TSLA')), null)
  assert.notEqual(depo.getItem(gostergeAnahtari('veli', 'AAPL')), null)
})

test('SIFIRLAMA (C6): bekleyen yazim iptal edilir - silinen kayit 300 ms sonra GERI YAZILMAZ', () => {
  const depo = new BellekDepo()
  const saat = new ElleSaat()
  const kayitci = new GecikmeliKayit(300, saat)
  kayitci.planla(gostergeAnahtari('ali', 'AAPL'), () => gostergeleriKaydet(depo, 'ali', 'AAPL', ['rsi14'], 1))
  kayitci.planla(anahtarUret('ali', 'AAPL'), () => kaydet(depo, 'ali', 'AAPL', [CIZIM]))
  // Baska sembolun bekleyen yazimi sifirlamadan etkilenmez.
  kayitci.planla(gostergeAnahtari('ali', 'TSLA'), () => gostergeleriKaydet(depo, 'ali', 'TSLA', ['macd'], 1))

  kayitlariSifirla(depo, kayitci, 'ali', 'AAPL')
  saat.hepsiniCalistir()
  assert.equal(depo.getItem(gostergeAnahtari('ali', 'AAPL')), null)
  assert.equal(depo.getItem(anahtarUret('ali', 'AAPL')), null)
  assert.notEqual(depo.getItem(gostergeAnahtari('ali', 'TSLA')), null)
})

test('SIFIRLAMA (C6): silme hatasi firlatmaz, raporlanir', () => {
  const depo = new BellekDepo()
  depo.removeItem = () => {
    throw new Error('SecurityError: engellendi')
  }
  const sonuc = kayitlariSifirla(depo, new GecikmeliKayit(300, new ElleSaat()), 'ali', 'AAPL')
  assert.equal(sonuc.basarili, false)
  assert.match(String(sonuc.hata), /silinemedi: Error: SecurityError: engellendi/)
})

test('SEKMELER: izlenen anahtar ya da tum depo temizligi (key=null) degisiklik sayilir', () => {
  const izlenen = [anahtarUret('ali', 'AAPL'), gostergeAnahtari('ali', 'AAPL')]
  assert.equal(baskaSekmeDegistirdi(gostergeAnahtari('ali', 'AAPL'), izlenen), true)
  assert.equal(baskaSekmeDegistirdi(anahtarUret('ali', 'AAPL'), izlenen), true)
  assert.equal(baskaSekmeDegistirdi(null, izlenen), true) // localStorage.clear()
  assert.equal(baskaSekmeDegistirdi(gostergeAnahtari('ali', 'TSLA'), izlenen), false)
  assert.equal(baskaSekmeDegistirdi(gostergeAnahtari('veli', 'AAPL'), izlenen), false)
})
