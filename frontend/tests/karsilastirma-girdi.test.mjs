import test from 'node:test'
import assert from 'node:assert/strict'
import { sembolleriAyristir, girdiUyarilari, hucre, olculenAlanSayisi,
         AZAMI_SEMBOL } from '../src/lib/karsilastirma-girdi.js'

test('virgul, bosluk ve noktali virgul ile ayrilir', () => {
  const s = sembolleriAyristir('msft, nvda; amd  googl')
  assert.deepEqual(s.semboller, ['MSFT', 'NVDA', 'AMD', 'GOOGL'])
})

test('gecersiz sembol SESSIZCE atilmaz, raporlanir', () => {
  const s = sembolleriAyristir('MSFT, A.., ..X, BRK.B')
  assert.deepEqual(s.semboller, ['MSFT', 'BRK.B'])
  assert.deepEqual(s.reddedilen, ['A..', '..X'])
  assert.match(girdiUyarilari(s)[0], /Geçersiz sembol/)
})

test('ozel bicimli gecerli semboller KORUNUR', () => {
  const s = sembolleriAyristir('BRK.B, BF-B, RDS.A')
  assert.deepEqual(s.semboller, ['BRK.B', 'BF-B', 'RDS.A'])
  assert.deepEqual(s.reddedilen, [])
})

test('yinelenen sembol bir kez alinir ve BILDIRILIR', () => {
  const s = sembolleriAyristir('MSFT, msft, MSFT, NVDA')
  assert.deepEqual(s.semboller, ['MSFT', 'NVDA'])
  assert.deepEqual(s.yinelenen, ['MSFT'])
  assert.ok(girdiUyarilari(s).some((x) => /Yinelenen/.test(x)))
})

test('tavan asilirsa kesilenler BILDIRILIR', () => {
  const girdi = Array.from({ length: AZAMI_SEMBOL + 3 }, (_, i) => `T${i}`).join(',')
  const s = sembolleriAyristir(girdi)
  assert.equal(s.semboller.length, AZAMI_SEMBOL)
  assert.equal(s.kesilen.length, 3)
  assert.ok(girdiUyarilari(s).some((x) => x.includes(`En fazla ${AZAMI_SEMBOL}`)))
})

test('uzun sembol reddedilir', () => {
  const s = sembolleriAyristir('ABCDEFGHIJK, MSFT')
  assert.deepEqual(s.semboller, ['MSFT'])
  assert.deepEqual(s.reddedilen, ['ABCDEFGHIJK'])
})

test('bos girdi cokmez', () => {
  const s = sembolleriAyristir('')
  assert.deepEqual(s.semboller, [])
  assert.deepEqual(girdiUyarilari(s), [])
  assert.deepEqual(sembolleriAyristir(null).semboller, [])
})

test('temiz girdide UYARI YOKTUR', () => {
  assert.deepEqual(girdiUyarilari(sembolleriAyristir('MSFT,NVDA')), [])
})

test('hucre: olculemedi ile GERCEK SIFIR ayrilir', () => {
  assert.equal(hucre(null), '—')
  assert.equal(hucre(undefined), '—')
  assert.equal(hucre(NaN), '—')
  assert.equal(hucre(0), '0', 'olculmus sifir tire ile gosterilemez')
})

test('hucre sayilari Turkce bicimler', () => {
  assert.equal(hucre(1234.567, 2), '1.234,57')
  assert.equal(hucre(0.000431, 6), '0,000431')
})

test('olculen alan sayimi sifiri OLCULMUS sayar', () => {
  const satir = { a: 0, b: null, c: 5, d: undefined, e: NaN }
  assert.equal(olculenAlanSayisi(satir, ['a', 'b', 'c', 'd', 'e']), 2)
})

test('sembol deseni servis-proxy ile AYNI kalmali', async () => {
  // Kopya desenlerin sessizce ayrismasini engelleyen kilit.
  const { readFileSync } = await import('node:fs')
  const { fileURLToPath } = await import('node:url')
  const { dirname, join } = await import('node:path')
  const kok = dirname(dirname(fileURLToPath(import.meta.url)))
  const proxy = readFileSync(join(kok, 'src', 'lib', 'servis-proxy.ts'), 'utf8')
  const m = proxy.match(/TICKER_DESENI\s*=\s*(\/.+\/)/)
  assert.ok(m, 'servis-proxy.ts icinde desen bulunamadi')
  const { SEMBOL_DESENI } = await import('../src/lib/karsilastirma-girdi.js')
  assert.equal(m[1], SEMBOL_DESENI.toString(),
    'iki desen ayrismis; biri digerini kabul etmeyen sembolleri gecirir')
})

test('sembol tavani MAKUL bir aralikta olmali', () => {
  /* MUTASYON M8: AZAMI_SEMBOL 8 -> 999 mutasyonu hayatta kalmisti, cunku
     tavan testi girdiyi AZAMI_SEMBOL'e gore URETIYORDU.

     Kesin degeri (8) civilemek asiri uyum olurdu — tavan bir ayardir. Ama
     SINIRSIZ olmasi zararlidir: her sembol sunucuda 4 es zamanli istek
     tetikliyor, yani 999 sembol ~4.000 es zamanli istek demek. Alt sinir da
     gerekli: 1 sembolluk bir "karsilastirma" ekrani anlamsizdir. */
  assert.ok(AZAMI_SEMBOL >= 2, 'karsilastirma icin en az 2 sembol gerekir')
  assert.ok(AZAMI_SEMBOL <= 20,
    `tavan cok yuksek (${AZAMI_SEMBOL}): sembol basina 4 sunucu istegi tetikleniyor`)
})

test('tavan SABIT bir sayiyla da dogrulanir', () => {
  /* Girdiyi AZAMI_SEMBOL'den TURETMEYEN ikinci bir kontrol: 25 sembol
     verildiginde kesinlikle kesme olmali. */
  const girdi = Array.from({ length: 25 }, (_, i) => `AA${i}`).join(',')
  const s = sembolleriAyristir(girdi)
  assert.ok(s.kesilen.length > 0, '25 sembolde kesme olmali')
  assert.ok(s.semboller.length <= 20)
})
