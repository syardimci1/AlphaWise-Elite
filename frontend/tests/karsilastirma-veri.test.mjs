import test from 'node:test'
import assert from 'node:assert/strict'
import { sembolSatiri, tabloGetir, varsayilanTabanlar }
  from '../src/lib/karsilastirma-veri.js'

const T = { qlib: 'http://q', taa: 'http://t', gamma: 'http://g', finra: 'http://f' }

function sahteFetch(harita) {
  return async (url) => {
    for (const [desen, yanit] of Object.entries(harita)) {
      if (url.includes(desen)) {
        if (yanit === 'HATA') throw new Error('baglanti reddedildi')
        if (yanit === 'ZAMAN') { const e = new Error('t'); e.name = 'TimeoutError'; throw e }
        if (typeof yanit === 'number') return { ok: false, status: yanit }
        return { ok: true, json: async () => yanit }
      }
    }
    return { ok: false, status: 404 }
  }
}

const TAM = {
  '/predict/': { score: 0.000431, as_of_date: '2026-09-03' },
  '/analyze/': { last_close: 510.12, rsi_14: 66.11, sma_20: 495.72, sma_50: 441.23 },
  '/dix-like/': { cari_hafta: { dpke_yuzde: 32.88 }, baglam: { ortalama_dpke_yuzde: 40.25 } },
  '/darkpool/': { dark_pool: { ats_toplam_shares: 19699467 }, week_start_date: '2026-08-17' },
}

test('tum servisler yanit verdiginde satir eksiksiz doldurulur', async () => {
  const r = await sembolSatiri('MSFT', { fetchImpl: sahteFetch(TAM), tabanlar: T })
  assert.equal(r.ticker, 'MSFT')
  assert.equal(r.qlib_skoru, 0.000431)
  assert.equal(r.son_kapanis, 510.12)
  assert.equal(r.dpke_yuzde, 32.88)
  assert.equal(r.ats_hisse, 19699467)
  assert.deepEqual(r.hatalar, { qlib: null, taa: null, dpke: null, finra: null })
})

test('BIR servis dusunce digerleri KAYBOLMAZ', async () => {
  const r = await sembolSatiri('MSFT',
    { fetchImpl: sahteFetch({ ...TAM, '/analyze/': 'HATA' }), tabanlar: T })
  assert.equal(r.son_kapanis, null, 'olculemedi')
  assert.equal(r.rsi_14, null)
  assert.equal(r.qlib_skoru, 0.000431, 'diger servisler etkilenmemeli')
  assert.match(r.hatalar.taa, /reddedildi/)
  assert.equal(r.hatalar.qlib, null)
})

test('zaman asimi AYRI bir gerekce olarak bildirilir', async () => {
  const r = await sembolSatiri('X',
    { fetchImpl: sahteFetch({ ...TAM, '/predict/': 'ZAMAN' }), tabanlar: T,
      zamanAsimiMs: 50 })
  assert.equal(r.hatalar.qlib, 'zaman aşımı')
})

test('HTTP hata kodu gerekceye tasinir', async () => {
  const r = await sembolSatiri('X',
    { fetchImpl: sahteFetch({ ...TAM, '/darkpool/': 503 }), tabanlar: T })
  assert.equal(r.ats_hisse, null)
  assert.equal(r.hatalar.finra, 'HTTP 503')
})

test('OLCULMUS SIFIR null ile karistirilmaz', async () => {
  const sifirli = { ...TAM, '/predict/': { score: 0, as_of_date: '2026-09-03' } }
  const r = await sembolSatiri('X', { fetchImpl: sahteFetch(sifirli), tabanlar: T })
  assert.equal(r.qlib_skoru, 0, 'olculmus sifir korunmali')
  assert.notEqual(r.qlib_skoru, null)
  assert.equal(r.hatalar.qlib, null)
})

test('eksik alan null olur, satir COKMEZ', async () => {
  const eksik = { ...TAM, '/analyze/': { last_close: 100 } }  // rsi/sma yok
  const r = await sembolSatiri('X', { fetchImpl: sahteFetch(eksik), tabanlar: T })
  assert.equal(r.son_kapanis, 100)
  assert.equal(r.rsi_14, null)
  assert.equal(r.hatalar.taa, null, 'alan eksikligi servis hatasi DEGILDIR')
})

test('tablo semboller arasi PARALEL toplanir', async () => {
  let esZamanli = 0, enYuksek = 0
  const yavas = async (url, o) => {
    esZamanli++; enYuksek = Math.max(enYuksek, esZamanli)
    await new Promise((r) => setTimeout(r, 20))
    esZamanli--
    return sahteFetch(TAM)(url, o)
  }
  const t0 = Date.now()
  const satirlar = await tabloGetir(['A', 'B', 'C'], { fetchImpl: yavas, tabanlar: T })
  assert.equal(satirlar.length, 3)
  assert.ok(enYuksek > 4, `paralel olmali, olculen en yuksek es zamanlilik: ${enYuksek}`)
  assert.ok(Date.now() - t0 < 200, 'sirali olsaydi cok daha uzun surerdi')
})

test('varsayilan tabanlar ic ag ve host icin AYRI', () => {
  assert.match(varsayilanTabanlar(true).qlib, /alphawise-qlib/)
  assert.match(varsayilanTabanlar(false).qlib, /127\.0\.0\.1:8050/)
})

// ===== CANLI OLCUMDE BULUNAN IKI SESSIZ HATA =====

test('HTTP 200 icindeki "error" alani SESSIZCE yutulmaz', async () => {
  /* qlib kapsam disi sembolde 200 + {"error":"...","score":null} doner;
     ok=true'ya bakip gecince kullanici BOS hucre gorup nedenini bulamiyordu. */
  const f = sahteFetch({ ...TAM,
    '/predict/': { error: 'bu hisse icin skor yok (kapsam disi olabilir)', score: null } })
  const r = await sembolSatiri('BRK.B', { fetchImpl: f, tabanlar: T })
  assert.equal(r.qlib_skoru, null)
  assert.match(r.hatalar.qlib, /kapsam disi/)
})

test('taa "veri bulunamadi" da gerekce olarak tasinir', async () => {
  const f = sahteFetch({ ...TAM, '/analyze/': { error: 'BRK.B icin veri bulunamadi' } })
  const r = await sembolSatiri('BRK.B', { fetchImpl: f, tabanlar: T })
  assert.equal(r.son_kapanis, null)
  assert.match(r.hatalar.taa, /veri bulunamadi/)
})

test('veri_var=false iken SIFIR HISSE olculmus gibi gosterilmez', async () => {
  /* EN TEHLIKELI: FINRA var olmayan sembolde veri_var=false doner ama
     ats_toplam_shares alanina 0 yazar. 0'i gostermek "bu hissede hic dark
     pool islemi yok" demek olurdu. */
  const f = sahteFetch({ ...TAM,
    '/darkpool/': { veri_var: false, week_start_date: '2026-08-17',
                    dark_pool: { ats_toplam_shares: 0 } } })
  const r = await sembolSatiri('YOKBOYLE', { fetchImpl: f, tabanlar: T })
  assert.equal(r.ats_hisse, null, 'veri_var=false iken 0 gosterilemez')
  assert.match(r.hatalar.finra, /FINRA verisi yok/)
})

test('veri_var=TRUE iken GERCEK sifir korunur', async () => {
  /* Ters yon: gercekten olculmus sifir hala 0 olmali. */
  const f = sahteFetch({ ...TAM,
    '/darkpool/': { veri_var: true, week_start_date: '2026-08-17',
                    dark_pool: { ats_toplam_shares: 0 } } })
  const r = await sembolSatiri('X', { fetchImpl: f, tabanlar: T })
  assert.equal(r.ats_hisse, 0, 'olculmus sifir null yapilmamali')
  assert.equal(r.hatalar.finra, null)
})

test('dpke veri_var=false de gerekce uretir', async () => {
  const f = sahteFetch({ ...TAM, '/dix-like/': { veri_var: false } })
  const r = await sembolSatiri('X', { fetchImpl: f, tabanlar: T })
  assert.equal(r.dpke_yuzde, null)
  assert.match(r.hatalar.dpke, /DPKE verisi yok/)
})
