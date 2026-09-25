// Kategori: KARŞILAŞTIRMA S5 (C5, Y8) — ADR-5 deseniyle kalıcılık: ad alanı, sürüm, ayıklama, sıfırlama.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  karsilastirmaAnahtari,
  karsilastirmaKaydet,
  karsilastirmaSil,
  karsilastirmaYukle,
} from '../../src/lib/grafik/karsilastirma-kalicilik'
import { anahtarUret, kaydet, type Depo } from '../../src/lib/grafik/cizim-kalicilik'
import { gostergeAnahtari, gostergeleriKaydet } from '../../src/lib/grafik/gosterge-kalicilik'
import { kayitlariSifirla } from '../../src/lib/grafik/kalicilik-sifirlama'
import { GecikmeliKayit, type Zamanlayici } from '../../src/lib/grafik/gecikmeli-kayit'
import type { KarsilastirmaSecimi } from '../../src/lib/grafik/karsilastirma'
import { ARAYUZ_METINLERI } from '../../src/lib/grafik/terminal-durum'

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

const ZAMAN = 1758800000000
const SECIM: KarsilastirmaSecimi = {
  mod: 'karsilastirma',
  semboller: [
    { sembol: 'MSFT', yuva: 1 },
    { sembol: 'NVDA', yuva: 2 },
  ],
}

test('C5 / Y8: anahtar ADR-5 ad alanı deseninde; tür ayrı, kimlik ve sembol kaçışlı', () => {
  assert.equal(karsilastirmaAnahtari('kullanici-7', 'aapl'), 'alphawise:grafik:karsilastirma:v1:kullanici-7:AAPL')
  assert.notEqual(karsilastirmaAnahtari('ali', 'AAPL'), gostergeAnahtari('ali', 'AAPL'))
  assert.notEqual(karsilastirmaAnahtari('ali', 'AAPL'), anahtarUret('ali', 'AAPL'))
  assert.notEqual(karsilastirmaAnahtari('a', 'B:C'), karsilastirmaAnahtari('a:B', 'C'))
})

test('C5: kaydet/yükle gidiş-dönüşü kayıpsız (mod + semboller + yuvalar), zarf sürümlü', () => {
  const depo = new BellekDepo()
  assert.deepEqual(karsilastirmaKaydet(depo, 'ali', 'AAPL', SECIM, ZAMAN), { basarili: true })
  assert.deepEqual(JSON.parse(String(depo.getItem(karsilastirmaAnahtari('ali', 'AAPL')))), {
    v: 1,
    mod: 'karsilastirma',
    semboller: SECIM.semboller,
    guncelleme_utc: ZAMAN,
  })
  assert.deepEqual(karsilastirmaYukle(depo, 'ali', 'AAPL'), { secim: SECIM })
})

test('C5: kayıt kullanıcıya ve ANA sembole aittir — başka kullanıcı/sembol görmez', () => {
  const depo = new BellekDepo()
  karsilastirmaKaydet(depo, 'ali', 'AAPL', SECIM, ZAMAN)
  assert.deepEqual(karsilastirmaYukle(depo, 'veli', 'AAPL'), { secim: { mod: 'tek', semboller: [] } })
  assert.deepEqual(karsilastirmaYukle(depo, 'ali', 'MSFT'), { secim: { mod: 'tek', semboller: [] } })
})

test('C5 göç tablosu: bozuk JSON, nesne olmayan, bilinmeyen sürüm, eksik alan → sıfırla + uyarı; okuma yan etkisiz', () => {
  const durumlar: [string, RegExp][] = [
    ['{bozuk', /bozuk kayit/],
    ['42', /bozuk kayit/],
    [JSON.stringify({ v: 9, mod: 'tek', semboller: [] }), /bilinmeyen surum \(v=9\)/],
    [JSON.stringify({ v: 1, mod: 'tek' }), /bozuk kayit/],
    [JSON.stringify({ v: 1, mod: 'baska', semboller: [] }), /bozuk kayit/],
  ]
  for (const [ham, uyari] of durumlar) {
    const depo = new BellekDepo()
    depo.setItem(karsilastirmaAnahtari('ali', 'AAPL'), ham)
    const sonuc = karsilastirmaYukle(depo, 'ali', 'AAPL')
    assert.deepEqual(sonuc.secim, { mod: 'tek', semboller: [] }, ham)
    assert.match(String(sonuc.uyari), uyari, ham)
    assert.equal(depo.getItem(karsilastirmaAnahtari('ali', 'AAPL')), ham, 'yukle depoya YAZMAZ')
  }
})

test('C5 / C2: geçersiz, yinelenen, ana sembole eşit, yuvası çakışan ya da 2 yi aşan öğeler ayıklanır ve SAYILIR', () => {
  const depo = new BellekDepo()
  depo.setItem(
    karsilastirmaAnahtari('ali', 'AAPL'),
    JSON.stringify({
      v: 1,
      mod: 'karsilastirma',
      semboller: [
        { sembol: 'MSFT', yuva: 1 },
        { sembol: 'msft', yuva: 2 }, // yinelenen (normalize sonrası)
        { sembol: 'AAPL', yuva: 2 }, // ana sembol
        { sembol: 'A..', yuva: 2 }, // geçersiz biçim
        { sembol: 'TSLA', yuva: 1 }, // yuva çakışması
        { sembol: 'AMD', yuva: 7 }, // tanımsız yuva
        { sembol: 'NVDA', yuva: 2 },
        { sembol: 'META', yuva: 2 }, // 2'yi aşan
        'duz-metin',
      ],
    }),
  )
  const sonuc = karsilastirmaYukle(depo, 'ali', 'AAPL')
  assert.deepEqual(sonuc.secim, SECIM)
  assert.match(String(sonuc.uyari), /7 karsilastirma sembolu gecersiz/)
})

test('C5: depo okunamıyorsa (gizli mod) boş seçim + uyarı; kota hatası kotaDoldu ile işaretlenir', () => {
  const kapali: Depo = {
    getItem: () => {
      throw new Error('SecurityError')
    },
    setItem: () => {
      const hata = new Error('dolu')
      hata.name = 'QuotaExceededError'
      throw hata
    },
    removeItem: () => {},
  }
  const yuklenen = karsilastirmaYukle(kapali, 'ali', 'AAPL')
  assert.deepEqual(yuklenen.secim, { mod: 'tek', semboller: [] })
  assert.match(String(yuklenen.uyari), /depo okunamadi/)
  const kayit = karsilastirmaKaydet(kapali, 'ali', 'AAPL', SECIM, ZAMAN)
  assert.equal(kayit.basarili, false)
  assert.equal(kayit.kotaDoldu, true)
})

test('C5: sil yalnızca kendi anahtarını siler', () => {
  const depo = new BellekDepo()
  karsilastirmaKaydet(depo, 'ali', 'AAPL', SECIM, ZAMAN)
  gostergeleriKaydet(depo, 'ali', 'AAPL', ['sma20'], 1)
  assert.deepEqual(karsilastirmaSil(depo, 'ali', 'AAPL'), { basarili: true })
  assert.equal(depo.getItem(karsilastirmaAnahtari('ali', 'AAPL')), null)
  assert.notEqual(depo.getItem(gostergeAnahtari('ali', 'AAPL')), null)
})

test('SIFIRLAMA (C6 kalıcılık + C5): "Kayıtlı ayarları sıfırla" karşılaştırma kaydını da siler, bekleyen yazımı iptal eder', () => {
  const depo = new BellekDepo()
  const saat = new ElleSaat()
  const kayitci = new GecikmeliKayit(300, saat)
  karsilastirmaKaydet(depo, 'ali', 'AAPL', SECIM, ZAMAN)
  karsilastirmaKaydet(depo, 'ali', 'TSLA', SECIM, ZAMAN)
  kaydet(depo, 'ali', 'AAPL', [])
  kayitci.planla(karsilastirmaAnahtari('ali', 'AAPL'), () =>
    karsilastirmaKaydet(depo, 'ali', 'AAPL', SECIM, ZAMAN),
  )
  assert.deepEqual(kayitlariSifirla(depo, kayitci, 'ali', 'AAPL'), { basarili: true })
  saat.hepsiniCalistir()
  assert.equal(depo.getItem(karsilastirmaAnahtari('ali', 'AAPL')), null, 'silinen kayıt geri yazılmamalı')
  assert.notEqual(depo.getItem(karsilastirmaAnahtari('ali', 'TSLA')), null, 'başka ana sembol dokunulmaz')
})

test('SIFIRLAMA metni: kullanıcı karşılaştırma seçiminin de silineceğini ONAYDAN ÖNCE görür', () => {
  assert.match(ARAYUZ_METINLERI.sifirlaOnay, /karşılaştırma/)
  assert.match(ARAYUZ_METINLERI.sifirlaAria, /karşılaştırma/)
})
