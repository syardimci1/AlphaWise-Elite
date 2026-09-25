// Kategori: KARŞILAŞTIRMA S1 / S6 (C2, C3, C6) — sembol ekleme/çıkarma, limit, renk yuvası, mod.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  AZAMI_GRUP,
  KARSILASTIRMA_METINLERI,
  bosSecim,
  grupDolu,
  modSec,
  sembolCikar,
  sembolEkle,
  sembolNormalize,
  type KarsilastirmaSecimi,
} from '../../src/lib/grafik/karsilastirma'
import { tickerDogrula } from '../../src/lib/servis-proxy'

function ekle(secim: KarsilastirmaSecimi, ham: string, ana = 'AAPL'): KarsilastirmaSecimi {
  const sonuc = sembolEkle(secim, ana, ham)
  if ('metin' in sonuc) assert.fail(`${ham} eklenemedi: ${sonuc.metin}`)
  return sonuc.secim
}

test('S1: ekleme normalize eder (boşluk, küçük harf) ve en düşük boş yuvayı verir', () => {
  const s1 = ekle(bosSecim(), '  msft ')
  assert.deepEqual(s1.semboller, [{ sembol: 'MSFT', yuva: 1 }])
  const s2 = ekle(s1, 'nvda')
  assert.deepEqual(s2.semboller, [{ sembol: 'MSFT', yuva: 1 }, { sembol: 'NVDA', yuva: 2 }])
})

test('C2 / FAZ4: 4. sembol REDDEDİLİR (otomatik çıkarma yok), seçim DEĞİŞMEZ ve neden metni döner', () => {
  const dolu = ekle(ekle(bosSecim(), 'MSFT'), 'NVDA')
  assert.equal(AZAMI_GRUP, 3)
  assert.equal(grupDolu(dolu), true, 'ekleme düğmesi dolulukta devre dışı olmalı')
  assert.equal(grupDolu(ekle(bosSecim(), 'MSFT')), false)
  const sonuc = sembolEkle(dolu, 'AAPL', 'TSLA')
  assert.equal(sonuc.tamam, false)
  if (sonuc.tamam) return
  assert.equal(sonuc.neden, 'dolu')
  assert.equal(sonuc.metin, KARSILASTIRMA_METINLERI.dolu)
  // En eski (MSFT) hâlâ yerinde: kullanıcının seçimi habersiz değişmedi.
  assert.deepEqual(dolu.semboller.map((s) => s.sembol), ['MSFT', 'NVDA'])
})

test('FAZ4: aynı sembolü iki kez ekleme — büyük/küçük harf ve boşluktan bağımsız reddedilir', () => {
  const s = ekle(bosSecim(), 'MSFT')
  for (const tekrar of ['MSFT', 'msft', ' Msft ']) {
    const sonuc = sembolEkle(s, 'AAPL', tekrar)
    assert.equal(sonuc.tamam, false)
    if (!sonuc.tamam) assert.equal(sonuc.neden, 'yinelenen')
  }
})

test('FAZ4: ana sembolün kendisi karşılaştırmaya eklenemez (kendisiyle karşılaştırma anlamsız)', () => {
  const sonuc = sembolEkle(bosSecim(), 'aapl', 'AAPL')
  assert.equal(sonuc.tamam, false)
  if (!sonuc.tamam) assert.equal(sonuc.neden, 'ana')
})

test('S1: geçersiz biçim reddedilir; istemci deseni sunucudaki tickerDogrula ile AYNI kararı verir', () => {
  const girdiler = ['', '   ', 'A..', 'A.', 'A--B', '../x', 'BRK.B', 'BF-B', 'aapl', 'ABCDEFGHIJK', 'ABCDEFGHIJ', 'A B', 'ÇAĞ', '1', 'X:Y']
  for (const girdi of girdiler) {
    // Sunucu kırpmaz; istemci önce kırpar. Karşılaştırma kırpılmış girdi üzerinden yapılır.
    assert.equal(sembolNormalize(girdi), tickerDogrula(girdi.trim()), `"${girdi}" için ayrıştılar`)
  }
  const sonuc = sembolEkle(bosSecim(), 'AAPL', 'A..')
  assert.equal(sonuc.tamam, false)
  if (!sonuc.tamam) assert.equal(sonuc.neden, 'gecersiz')
})

test('C3: renk VARLIĞA bağlıdır — birini çıkarmak diğerinin yuvasını değiştirmez; boşalan yuva yeniden kullanılır', () => {
  const dolu = ekle(ekle(bosSecim(), 'MSFT'), 'NVDA')
  const cikti = sembolCikar(dolu, 'MSFT')
  assert.deepEqual(cikti.semboller, [{ sembol: 'NVDA', yuva: 2 }], 'NVDA rengini korumalı')
  const yeni = ekle(cikti, 'TSLA')
  assert.deepEqual(yeni.semboller.find((s) => s.sembol === 'TSLA'), { sembol: 'TSLA', yuva: 1 })
})

test('S1: olmayan sembolü çıkarmak etkisizdir (girdinin kendisi döner)', () => {
  const s = ekle(bosSecim(), 'MSFT')
  assert.equal(sembolCikar(s, 'ZZZ'), s)
})

test('C6: mod geçişi seçimi KORUR; aynı moda geçiş etkisizdir', () => {
  const s = ekle(ekle(bosSecim(), 'MSFT'), 'NVDA')
  const k = modSec(s, 'karsilastirma')
  assert.equal(k.mod, 'karsilastirma')
  const t = modSec(k, 'tek')
  assert.equal(t.mod, 'tek')
  assert.deepEqual(t.semboller, s.semboller, 'tek moda dönüş listeyi silmemeli')
  assert.deepEqual(modSec(t, 'karsilastirma').semboller, s.semboller)
  assert.equal(modSec(t, 'tek'), t)
})

test('Saflık: işlemler girdiyi mutasyona uğratmaz', () => {
  const s = ekle(bosSecim(), 'MSFT')
  const kopya = JSON.stringify(s)
  sembolEkle(s, 'AAPL', 'NVDA')
  sembolCikar(s, 'MSFT')
  modSec(s, 'karsilastirma')
  assert.equal(JSON.stringify(s), kopya)
})
