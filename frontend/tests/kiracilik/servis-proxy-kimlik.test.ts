// Kategori: SERVİS PROXY — kimlik taşıma ve hata gövdesi süzgeci (İ-2)
//
// Gerçek bir saplama servise karşı çalışır; böylece "başlık yukarı akışa
// gitti mi" sorusu ölçülür, varsayılmaz.
//
// Süzgecin varlık nedeni ÖLÇÜLEN bir sızıntıdır (16.09.2026):
//   gamma-exposure-service/main.py:223,257 → detail içinde kota_durumu()
//   kota_durumu() → tek_anahtar_kota_durumu() → {"anahtar": "FLASHALPHA_API_KEY_2",
//   "kullanilan": N}. "anahtar" bir SIR ADI; "kullanilan" TÜM kiracıların
//   ortak tüketimi, yani B kullanıcısı A'nın harcamasını ölçebilir (yan kanal).
//   dashboard/page.tsx:334-339 bu değeri JSON.stringify ile EKRANA basıyor.
import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { createServer, type Server } from 'node:http'
import { AddressInfo } from 'node:net'
import { NextRequest } from 'next/server'
import { servisProxy, istekKimligi, detayiSuz } from '../../src/lib/servis-proxy'
import { KULLANICI_BASLIGI, KIRACI_BASLIGI, type Kimlik } from '../../src/lib/kiraci'

const A = 'c59c7853-b752-44ca-b40d-c4eb09798b50'

// gamma-exposure-service/main.py:246-259'un GERÇEK 402 gövdesi.
const GERCEK_402 = {
  detail: {
    hata: 'Sembol FlashAlpha ucretsiz planinin kapsaminda degil',
    aciklama: 'Bu bilgi daha once olculdu ve gun sonuna kadar saklaniyor; tekrar sormak gunluk hakki bosa yakardi.',
    ticker: 'NVDA',
    istek_yapilmadi: true,
    onbellekten: true,
    kota_durumu: {
      tarih_utc: '2026-09-16',
      tanimli_anahtar_sayisi: 5,
      toplam_gunluk_kota: 25,
      toplam_kullanilan: 19,
      toplam_kalan: 6,
      kota_doldu: false,
      anahtar_basina: [
        { anahtar: 'FLASHALPHA_API_KEY_1', kullanilan: 5, gunluk_kota: 5, kalan: 0, kota_doldu: true },
        { anahtar: 'FLASHALPHA_API_KEY_2', kullanilan: 4, gunluk_kota: 5, kalan: 1, kota_doldu: false },
      ],
    },
  },
}

let sunucu: Server
let taban: string
let gorulenBasliklar: Record<string, string | string[] | undefined> = {}
let yanitDurumu = 200
let yanitGovdesi: unknown = { ok: true }

before(async () => {
  sunucu = createServer((istek, yanit) => {
    gorulenBasliklar = { ...istek.headers }
    yanit.writeHead(yanitDurumu, { 'content-type': 'application/json' })
    yanit.end(JSON.stringify(yanitGovdesi))
  })
  await new Promise<void>(c => sunucu.listen(0, '127.0.0.1', c))
  taban = `http://127.0.0.1:${(sunucu.address() as AddressInfo).port}`
})
after(() => { sunucu?.close() })

const KULLANICI: Kimlik = { kullaniciId: A, kiraci: 'kullanici' }
const SISTEM: Kimlik = { kullaniciId: 'sistem', kiraci: 'sistem' }

function cagir(kimlik?: Kimlik) {
  yanitDurumu = 200; yanitGovdesi = { ok: true }
  return servisProxy({ taban, yol: '/deneme', zamanAsimiMs: 5000, servisAdi: 'Deneme', kimlik })
}

// ------------------------------------------------- (d) baslik yukari gidiyor
test('I-2: kimlik verilince baslik YUKARI AKISA gonderiliyor', async () => {
  await cagir(KULLANICI)
  assert.equal(gorulenBasliklar[KULLANICI_BASLIGI], A)
  assert.equal(gorulenBasliklar[KIRACI_BASLIGI], 'kullanici')
})

// ------------------------------------------- (a) geriye uyumluluk: kimlik yok
test('GERIYE UYUMLULUK: kimlik verilmezse HICBIR kiraci basligi gitmez', async () => {
  await cagir(undefined)
  assert.equal(gorulenBasliklar[KULLANICI_BASLIGI], undefined)
  assert.equal(gorulenBasliklar[KIRACI_BASLIGI], undefined)
})

// ------------------------------------------------------ (c) SIZINTI SUZGECI
test('SIZINTI: kullanici kiracisinda API ANAHTARI ADI ve ORTAK SAYAC gecmez', async () => {
  yanitDurumu = 402; yanitGovdesi = GERCEK_402
  const y = await servisProxy({
    taban, yol: '/gex', zamanAsimiMs: 5000, servisAdi: 'GEX', kimlik: KULLANICI,
  })
  const govde = await y.json()
  const metin = JSON.stringify(govde)

  assert.equal(y.status, 402)
  // Sizmamasi gerekenler
  assert.ok(!metin.includes('FLASHALPHA'), `API anahtari adi sizdi: ${metin}`)
  assert.ok(!metin.includes('kota_durumu'), 'ortak kota sayaci sizdi')
  assert.ok(!metin.includes('toplam_kullanilan'), 'capraz-kiraci yan kanal sizdi')
  assert.ok(!metin.includes('anahtar_basina'), 'anahtar basina dokum sizdi')
  // Gecmesi gerekenler — "neden veri yok" sorusu cevapsiz KALMAMALI
  assert.ok(metin.includes('kapsaminda degil'), 'kullaniciya anlamli sebep gitmeli')
  assert.ok(String(govde.detay).includes('gunluk hakki'), 'aciklama alani gecmeli')
})

// ----------------------------------------- (b) sistem kiracisi: ic teshis tam
test('IC TESHIS: sistem kiracisinda ham detay AYNEN korunur', async () => {
  yanitDurumu = 402; yanitGovdesi = GERCEK_402
  const y = await servisProxy({
    taban, yol: '/gex', zamanAsimiMs: 5000, servisAdi: 'GEX', kimlik: SISTEM,
  })
  const metin = JSON.stringify(await y.json())
  assert.ok(metin.includes('FLASHALPHA_API_KEY_2'), 'ic teshis icin ham detay kalmali')
  assert.ok(metin.includes('kota_durumu'))
})

test('GERIYE UYUMLULUK: kimlik YOKSA da ham detay aynen korunur', async () => {
  yanitDurumu = 402; yanitGovdesi = GERCEK_402
  const y = await servisProxy({ taban, yol: '/gex', zamanAsimiMs: 5000, servisAdi: 'GEX' })
  assert.ok(JSON.stringify(await y.json()).includes('FLASHALPHA_API_KEY_2'))
})

// ------------------------------------------------ (e) ag hatasi: ic adres/port
test('SIZINTI: ag hatasinda IC ADRES/PORT kullaniciya gitmez', async () => {
  // 127.0.0.1:1 kapali bir port — ECONNREFUSED uretir ve err.message
  // "connect ECONNREFUSED 127.0.0.1:1" seklindedir.
  const y = await servisProxy({
    taban: 'http://127.0.0.1:1', yol: '/x', zamanAsimiMs: 3000,
    servisAdi: 'Kapali', kimlik: KULLANICI,
  })
  const govde = await y.json()
  assert.equal(y.status, 502)
  assert.equal(govde.detay, null, 'ic adres/port bastirilmali')
  assert.ok(String(govde.hata).includes('ulasilamiyor'), 'kullanici yine de sebebi gormeli')
})

test('IC TESHIS: ag hatasinda sistem kiracisi ham mesaji gorur', async () => {
  const y = await servisProxy({
    taban: 'http://127.0.0.1:1', yol: '/x', zamanAsimiMs: 3000,
    servisAdi: 'Kapali', kimlik: SISTEM,
  })
  const govde = await y.json()
  assert.ok(govde.detay !== null, 'ic teshis icin mesaj kalmali')
})

// ----------------------------------------------------------- istekKimligi
test('istekKimligi: middleware basligini dogru okur', () => {
  const r = new NextRequest('http://localhost/api/portfoy', {
    headers: { [KULLANICI_BASLIGI]: A, [KIRACI_BASLIGI]: 'kullanici' },
  })
  const k = istekKimligi(r)
  assert.equal(k?.kullaniciId, A)
  assert.equal(k?.kiraci, 'kullanici')
})

test('istekKimligi: baslik yoksa null (karar cagirana ait)', () => {
  assert.equal(istekKimligi(new NextRequest('http://localhost/api/portfoy')), null)
})

test('istekKimligi: bozuk kimlik null doner, sisteme DUSMEZ', () => {
  const r = new NextRequest('http://localhost/api/portfoy', {
    headers: { [KULLANICI_BASLIGI]: '../../etc/passwd', [KIRACI_BASLIGI]: 'kullanici' },
  })
  assert.equal(istekKimligi(r), null)
})

// ------------------------------------------------------------- detayiSuz
test('detayiSuz: metin detay kullaniciya gecer ama 300 karakterle sinirli', () => {
  const uzun = 'A'.repeat(500)
  assert.equal(detayiSuz(uzun, KULLANICI)?.length, 300)
})

test('detayiSuz: izin listesinde HIC alan yoksa null doner', () => {
  const s = detayiSuz({ anahtar: 'GIZLI', kullanilan: 9 }, KULLANICI)
  assert.equal(s, null, 'izin listesi disi alanlardan metin uretilmemeli')
})
