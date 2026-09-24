// Kategori: KALICILIK YAZMA STRATEJISI (C5 / Y10) - anahtar basina debounce + bosaltma.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { GecikmeliKayit, KAYIT_GECIKMESI_MS, type Zamanlayici } from '../../src/lib/grafik/gecikmeli-kayit'

/** Elle ilerletilen saat: gercek zaman beklemeden, deterministik. */
class SahteSaat implements Zamanlayici {
  simdi = 0
  private sayac = 0
  private readonly isler = new Map<number, { zaman: number; is: () => void }>()
  kur(is: () => void, ms: number): unknown {
    this.sayac += 1
    this.isler.set(this.sayac, { zaman: this.simdi + ms, is })
    return this.sayac
  }
  iptal(tutamac: unknown): void {
    this.isler.delete(tutamac as number)
  }
  ilerle(ms: number): void {
    this.simdi += ms
    for (const [kimlik, { zaman, is }] of [...this.isler]) {
      if (zaman <= this.simdi) {
        this.isler.delete(kimlik)
        is()
      }
    }
  }
}

test('GECIKMELI KAYIT: varsayilan gecikme 300 ms (C5 sozlesmesi)', () => {
  assert.equal(KAYIT_GECIKMESI_MS, 300)
})

test('GECIKMELI KAYIT: yazim hemen DEGIL, pencere dolunca bir kez yapilir', () => {
  const saat = new SahteSaat()
  const kayit = new GecikmeliKayit(300, saat)
  const yazilan: string[] = []
  kayit.planla('k', () => yazilan.push('bir'))
  saat.ilerle(299)
  assert.deepEqual(yazilan, [])
  saat.ilerle(1)
  assert.deepEqual(yazilan, ['bir'])
  saat.ilerle(1000)
  assert.deepEqual(yazilan, ['bir'])
})

test('GECIKMELI KAYIT: pencere icindeki ardisik planlar TEK yazima iner ve SONUNCUSU yazilir', () => {
  const saat = new SahteSaat()
  const kayit = new GecikmeliKayit(300, saat)
  const yazilan: number[] = []
  for (let i = 0; i < 50; i += 1) {
    kayit.planla('k', () => yazilan.push(i))
    saat.ilerle(100) // her plan bir oncekinin penceresini yeniden baslatir
  }
  assert.deepEqual(yazilan, [])
  saat.ilerle(300)
  assert.deepEqual(yazilan, [49])
})

test('GECIKMELI KAYIT: farkli anahtarlar birbirini IPTAL ETMEZ (sembol/tur degisimi veri kaybetmez)', () => {
  const saat = new SahteSaat()
  const kayit = new GecikmeliKayit(300, saat)
  const yazilan: string[] = []
  kayit.planla('AAPL', () => yazilan.push('AAPL'))
  kayit.planla('TSLA', () => yazilan.push('TSLA'))
  saat.ilerle(300)
  assert.deepEqual(yazilan.sort(), ['AAPL', 'TSLA'])
})

test('GECIKMELI KAYIT: bosalt bekleyen TUM yazimlari hemen yapar; sonra zamanlayici bir sey yapmaz', () => {
  const saat = new SahteSaat()
  const kayit = new GecikmeliKayit(300, saat)
  const yazilan: string[] = []
  kayit.planla('a', () => yazilan.push('a'))
  kayit.planla('b', () => yazilan.push('b'))
  assert.equal(kayit.bekleyenSayisi(), 2)
  kayit.bosalt()
  assert.deepEqual(yazilan, ['a', 'b'])
  assert.equal(kayit.bekleyenSayisi(), 0)
  saat.ilerle(1000)
  assert.deepEqual(yazilan, ['a', 'b']) // cift yazim yok
})

test('GECIKMELI KAYIT: iptal yalnizca o anahtarin bekleyen yazimini duser (sifirlama yolu)', () => {
  const saat = new SahteSaat()
  const kayit = new GecikmeliKayit(300, saat)
  const yazilan: string[] = []
  kayit.planla('a', () => yazilan.push('a'))
  kayit.planla('b', () => yazilan.push('b'))
  kayit.iptal('a')
  kayit.iptal('yok') // olmayan anahtar: hata yok
  saat.ilerle(300)
  assert.deepEqual(yazilan, ['b'])
})

test('GECIKMELI KAYIT: yazim sirasinda firlayan hata digerlerini durdurmaz', () => {
  const kayit = new GecikmeliKayit(300, new SahteSaat())
  const yazilan: string[] = []
  kayit.planla('a', () => {
    throw new Error('beklenmedik')
  })
  kayit.planla('b', () => yazilan.push('b'))
  assert.throws(() => kayit.bosalt(), /beklenmedik/)
  assert.deepEqual(yazilan, ['b'])
  assert.equal(kayit.bekleyenSayisi(), 0)
})

test('GECIKMELI KAYIT: yazim sonrasi ayni anahtar yeniden planlanabilir', () => {
  const saat = new SahteSaat()
  const kayit = new GecikmeliKayit(300, saat)
  const yazilan: number[] = []
  kayit.planla('k', () => yazilan.push(1))
  saat.ilerle(300)
  kayit.planla('k', () => yazilan.push(2))
  saat.ilerle(300)
  assert.deepEqual(yazilan, [1, 2])
})
