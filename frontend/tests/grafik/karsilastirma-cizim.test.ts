// Kategori: KARŞILAŞTIRMA S3 / S4 / S6 (C3, C4, C6, Y8) — çizgi verisi, lejant, görünüm kararı, hukuki dil.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  KARSILASTIRMA_METINLERI,
  SAYDAM,
  SERI_RENKLERI,
  bosSecim,
  cizgiVerisi,
  gorunumKarari,
  hizalaVeNormalizeEt,
  lejantSatirlari,
  modSec,
  sembolEkle,
  sembolHataMetni,
  tabanNotu,
  yuzdeMetni,
  type GirdiSerisi,
  type HizalamaSonucu,
} from '../../src/lib/grafik/karsilastirma'

function seri(sembol: string, yuva: 0 | 1 | 2, ciftler: [string, number][]): GirdiSerisi {
  return { sembol, yuva, barlar: ciftler.map(([tarih, kapanis]) => ({ tarih, kapanis })) }
}

function tamam(sonuc: HizalamaSonucu): Extract<HizalamaSonucu, { durum: 'tamam' }> {
  assert.equal(sonuc.durum, 'tamam')
  return sonuc as Extract<HizalamaSonucu, { durum: 'tamam' }>
}

// Boşluklu örnek: B'de 02 ve 03 yok, C'de 06 yok (son bar 05 — bitiş, boşluk değil).
const ORNEK = tamam(
  hizalaVeNormalizeEt([
    seri('AAA', 0, [['2026-03-02', 100], ['2026-03-03', 101], ['2026-03-04', 102], ['2026-03-05', 103], ['2026-03-06', 104]]),
    seri('BBB', 1, [['2026-03-02', 10], ['2026-03-05', 12], ['2026-03-06', 13]]),
    seri('CCC', 2, [['2026-03-02', 50], ['2026-03-03', 55], ['2026-03-04', 60], ['2026-03-05', 40]]),
  ]),
)

test('C4 / S4: eksik gün WHITESPACE olur; boşluktan önceki son noktanın segmenti SAYDAM (köprü yok)', () => {
  const b = ORNEK.seriler[1]
  const veri = cizgiVerisi(ORNEK.eksen, b.degerler)
  assert.equal(veri.length, ORNEK.eksen.length, 'eksenle bire bir: zaman ölçeği hizası')
  assert.deepEqual(veri[1], { time: '2026-03-03' })
  assert.deepEqual(veri[2], { time: '2026-03-04' })
  assert.equal('value' in veri[1], false, 'eksik gün için sayı (0 dahil) uydurulmaz')
  // Ölçülen kütüphane davranışı (FAZ 1 §2.1): i. noktanın rengi i→i+1 segmentini boyar.
  assert.equal(veri[0].color, SAYDAM, 'boşluğu köprüleyen segment görünmez olmalı')
  assert.equal(veri[3].color, undefined, 'boşluk sonrası segmentler normal renkte')
  assert.equal(veri[4].color, undefined)
})

test('C4: serinin SONUNDAN sonraki boş günler için son nokta saydam YAPILMAZ (köprülenecek segment yok)', () => {
  const c = ORNEK.seriler[2]
  const veri = cizgiVerisi(ORNEK.eksen, c.degerler)
  assert.deepEqual(veri[4], { time: '2026-03-06' })
  assert.equal(veri[3].color, undefined, 'imleç işareti son noktada görünür kalmalı')
})

test('C4: yalnızca köprü segmentleri saydam — boşluksuz seride hiçbir nokta saydam değil', () => {
  const a = cizgiVerisi(ORNEK.eksen, ORNEK.seriler[0].degerler)
  assert.ok(a.every((n) => n.color === undefined && typeof n.value === 'number'))
})

test('C3: renkler sabit, yuvaya bağlı ve birbirinden farklı (doğrulanmış palet)', () => {
  assert.deepEqual(SERI_RENKLERI, { 0: '#3987e5', 1: '#d95926', 2: '#199e70' })
  assert.equal(new Set(Object.values(SERI_RENKLERI)).size, 3)
})

test('yuzdeMetni: işaret, Türkçe ondalık, sıfırın işaretsiz yazılması (-0 yok)', () => {
  assert.equal(yuzdeMetni(12.345), '+%12,35')
  assert.equal(yuzdeMetni(-3.1), '-%3,10')
  assert.equal(yuzdeMetni(0), '%0,00')
  assert.equal(yuzdeMetni(-0.001), '%0,00')
  assert.equal(yuzdeMetni(1234.5), '+%1234,50')
})

test('C3 / C4: lejant her seriyi renk + sembol + değerle verir; imleç eksik güne gelince "veri yok" der', () => {
  const imlecsiz = lejantSatirlari(ORNEK, null)
  assert.deepEqual(imlecsiz.map((s) => [s.sembol, s.renk, s.anaMi]), [
    ['AAA', '#3987e5', true],
    ['BBB', '#d95926', false],
    ['CCC', '#199e70', false],
  ])
  // İmleç yokken her seri KENDİ son değerini ve tarihini gösterir.
  assert.equal(imlecsiz[2].tarih, '2026-03-05')
  assert.equal(imlecsiz[2].degerMetni, '-%20,00')
  assert.equal(imlecsiz[1].degerMetni, '+%30,00')

  const imlecli = lejantSatirlari(ORNEK, '2026-03-03')
  assert.equal(imlecli[1].degerMetni, KARSILASTIRMA_METINLERI.veriYok)
  assert.equal(imlecli[0].degerMetni, '+%1,00')
  assert.equal(imlecli[1].tarih, '2026-03-03')
})

test('C4 / C1: lejant notları eksik günü, bitişi, taban öncesini, geçersizi ve sıçramayı SAYIYLA söyler', () => {
  const satirlar = lejantSatirlari(ORNEK, null)
  assert.ok(satirlar[1].notlar.some((n) => n.startsWith('2 gün veri yok') && n.includes('2026-03-03')))
  assert.ok(satirlar[2].notlar.some((n) => n.includes('son veri: 2026-03-05')))
  assert.deepEqual(satirlar[0].notlar, [])

  const karisik = tamam(
    hizalaVeNormalizeEt([
      seri('X', 0, [['2026-01-02', 10], ['2026-01-05', 10], ['2026-01-06', 20], ['2026-01-07', 0]]),
      seri('Y', 1, [['2026-01-05', 5], ['2026-01-06', 5], ['2026-01-07', 5]]),
    ]),
  )
  const notlar = lejantSatirlari(karisik, null)[0].notlar.join(' | ')
  assert.match(notlar, /1 bar ortak başlangıç öncesinde/)
  assert.match(notlar, /1 kapanış geçersiz/)
  assert.match(notlar, /1 günde tek günlük değişim %40/)
})

test('C1: taban notu tarihi, günlük kapanışı ve düzeltme belirsizliğini açıkça yazar', () => {
  const not = tabanNotu('2024-09-25')
  assert.match(not, /2024-09-25/)
  assert.match(not, /%0/)
  assert.match(not, /düzeltme/)
})

test('S6 / FAZ4: tek sembol → karşılaştırma anlamsız, MUM grafiğine düşülür ve nedeni yazılır', () => {
  const k = modSec(bosSecim(), 'karsilastirma')
  const karar = gorunumKarari(k, null, false)
  assert.equal(karar.grafik, 'mum')
  assert.equal(karar.not, KARSILASTIRMA_METINLERI.tekSeri)
  assert.deepEqual(gorunumKarari(bosSecim(), ORNEK, false), { grafik: 'mum', not: null })
})

test('S6: veri gelmeyen/yetersiz/ortak günü olmayan durumlar mum grafiğine düşer; tamam → karşılaştırma', () => {
  const eklenen = sembolEkle(modSec(bosSecim(), 'karsilastirma'), 'AAA', 'BBB')
  assert.equal(eklenen.tamam, true)
  if (!eklenen.tamam) return
  const s = eklenen.secim
  assert.deepEqual(gorunumKarari(s, null, true), { grafik: 'mum', not: KARSILASTIRMA_METINLERI.yukleniyor })
  const yetersiz = gorunumKarari(s, { durum: 'yetersiz', verisiz: ['BBB'] }, false)
  assert.equal(yetersiz.grafik, 'mum')
  assert.match(String(yetersiz.not), /BBB/)
  assert.equal(gorunumKarari(s, { durum: 'ortak-gun-yok', verisiz: [] }, false).grafik, 'mum')
  assert.deepEqual(gorunumKarari(s, ORNEK, false), { grafik: 'karsilastirma', not: null })
})

// Y8 HUKUKİ DİL — terminal-durum.test.ts ile aynı kalıplar (oradaki gerekçe: hukuki_dil.py'den türetildi).
const YASAKLI_KALIPLAR: { ad: string; kalip: RegExp }[] = [
  { ad: 'emir kipi', kalip: /\w+m[ae]l[iı]s[iı]n[iı]z/i },
  { ad: 'tavsiye', kalip: /tavsiye/i },
  { ad: 'en iyi', kalip: /en iyi/i },
  { ad: 'işlem emri', kalip: /\b(al|sat|gir|yatir|yatır|alin|alın|satin|satın)\b/i },
  { ad: 'kesin kazanç', kalip: /kesin kazan/i },
  { ad: 'risksiz', kalip: /risksiz/i },
  { ad: 'garanti', kalip: /garanti/i },
  { ad: 'fırsat', kalip: /f[iı]rsat/i },
  { ad: 'hedef fiyat', kalip: /hedef fiyat/i },
  // Karşılaştırmaya özgü: bir sembolü diğerinden "üstün/iyi" ilan eden dil.
  // `\b` Türkçe harfte (ü, ö) çalışmaz; Unicode harf sınırı kullanılır.
  { ad: 'üstünlük', kalip: /(?<!\p{L})(daha iyi|kazanan|kaybeden|üstün|geride kal|önde(?!\p{L}))/iu },
]

test('Y8: karşılaştırma modunun gösterdiği TÜM metinler yasaklı kalıplara takılmaz', () => {
  const metinler: string[] = [
    ...Object.values(KARSILASTIRMA_METINLERI),
    tabanNotu('2024-09-25'),
    sembolHataMetni('MSFT', 'HTTP 500'),
    String(gorunumKarari(modSec(bosSecim(), 'karsilastirma'), null, false).not),
  ]
  const eklenen = sembolEkle(modSec(bosSecim(), 'karsilastirma'), 'AAA', 'BBB')
  if (eklenen.tamam) {
    metinler.push(String(gorunumKarari(eklenen.secim, { durum: 'yetersiz', verisiz: ['BBB'] }, false).not))
    metinler.push(String(gorunumKarari(eklenen.secim, { durum: 'ortak-gun-yok', verisiz: [] }, false).not))
  }
  const karisik = tamam(
    hizalaVeNormalizeEt([
      seri('X', 0, [['2026-01-02', 10], ['2026-01-05', 10], ['2026-01-06', 20], ['2026-01-07', 0], ['2026-01-09', 21]]),
      seri('Y', 1, [['2026-01-05', 5], ['2026-01-06', 5], ['2026-01-07', 5], ['2026-01-08', 5]]),
    ]),
  )
  for (const satir of [...lejantSatirlari(karisik, null), ...lejantSatirlari(ORNEK, null)]) metinler.push(...satir.notlar)
  assert.ok(metinler.length >= 25, `metin sayısı beklenenden az: ${metinler.length}`)
  for (const metin of metinler) {
    for (const { ad, kalip } of YASAKLI_KALIPLAR) {
      assert.equal(kalip.test(metin), false, `"${metin}" metni "${ad}" kalıbına takıldı`)
    }
  }
})

test('Y8 kapısı gerçekten çalışıyor: yasaklı örnekler yakalanır', () => {
  for (const ornek of ['MSFT daha iyi performans', 'kazanan sembol', 'şimdi al', 'garantili getiri', 'üstün seri', 'NVDA önde']) {
    assert.equal(YASAKLI_KALIPLAR.some(({ kalip }) => kalip.test(ornek)), true, `"${ornek}" yakalanmalıydı`)
  }
})
