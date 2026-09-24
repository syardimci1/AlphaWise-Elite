// Kategori: GRAFİK TERMİNALİ DURUMU — araç/dilim/gösterge seçimi, çizim
// tamamlama akışı, türetilmiş veri etiketleri ve Y8 hukuki dil kapısı.
//
// NEDEN BURASI TEST EDİLİYOR: `GrafikTerminali.tsx` bu depoda render
// EDİLEMEZ (jsdom yok, test koşucusu çıplak node:test). Bileşenin TÜM kararı
// bilerek `terminal-durum.ts`'e taşındı; bu dosya o kararların tamamını
// sınar. Bileşende kalan yalnızca kütüphane/DOM mekaniğidir.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  ARAC_ETIKETLERI,
  ARAC_SIRASI,
  ARAYUZ_METINLERI,
  DILIM_ETIKETLERI,
  DILIM_SIRASI,
  GUN_ICI_DILIMLER,
  bosTerminalDurum,
  dilimEtiketi,
  gunIciNeden,
  terminalReducer,
  tiklamaSonucu,
  veriNotu,
  yuklemeNotu,
  kayitHataMetni,
} from '../../src/lib/grafik/terminal-durum'
import type { AracKimlik, TerminalDurum } from '../../src/lib/grafik/terminal-durum'
import { GEREKLI_NOKTA_SAYISI, gecerliCizim } from '../../src/lib/grafik/cizim-model'
import type { CizimTipi, Nokta } from '../../src/lib/grafik/cizim-model'
import { tumGostergeKimlikleri } from '../../src/lib/grafik/gosterge-tanim'

/** Sabit kimlik: Date.now/Math.random test tarafında da KULLANILMAZ. */
const KIMLIK = {
  id: 'c-1',
  olusturma_utc: 1_700_000_000_000,
  stil: { renk: '#D4AF37', kalinlik: 2 },
}

const N1: Nokta = { t_utc: 1_600_000_000_000, fiyat: 100 }
const N2: Nokta = { t_utc: 1_600_086_400_000, fiyat: 110 }

/** Aracı seçilmiş bir başlangıç durumu. */
function aracli(arac: AracKimlik): TerminalDurum {
  return terminalReducer(bosTerminalDurum(), { tip: 'ARAC_SEC', arac })
}

test('boş durum: günlük dilim, imleç aracı, gösterge ve bekleyen nokta yok', () => {
  assert.deepEqual(bosTerminalDurum(), {
    dilim: 'gunluk',
    arac: 'imlec',
    gostergeler: [],
    bekleyenNoktalar: [],
  })
})

test('ARAC_SIRASI imleç + TÜM çizim tiplerini kapsar (eksik araç düğmesiz kalır)', () => {
  const cizimTipleri = Object.keys(GEREKLI_NOKTA_SAYISI) as CizimTipi[]
  assert.equal(ARAC_SIRASI[0], 'imlec')
  assert.equal(ARAC_SIRASI.length, cizimTipleri.length + 1)
  for (const tip of cizimTipleri) {
    assert.ok(ARAC_SIRASI.includes(tip), `${tip} araç çubuğunda yok`)
    assert.equal(typeof ARAC_ETIKETLERI[tip], 'string')
  }
})

test('ARAC_SEC aracı değiştirir ve YARIM çizimi düşürür', () => {
  const bir = aracli('dikdortgen')
  const yarim = terminalReducer(bir, { tip: 'NOKTA_EKLE', nokta: N1 })
  assert.equal(yarim.bekleyenNoktalar.length, 1)
  const sonra = terminalReducer(yarim, { tip: 'ARAC_SEC', arac: 'yatay' })
  assert.equal(sonra.arac, 'yatay')
  assert.deepEqual(sonra.bekleyenNoktalar, [])
})

test('ARAC_SEC aynı aracı seçmek ETKİSİZDİR (aynı referans döner)', () => {
  const bir = aracli('trend')
  assert.equal(terminalReducer(bir, { tip: 'ARAC_SEC', arac: 'trend' }), bir)
})

test('DILIM_SEC dilimi değiştirir ve yarım çizimi düşürür; aynı dilim etkisiz', () => {
  const bir = aracli('trend')
  const yarim = terminalReducer(bir, { tip: 'NOKTA_EKLE', nokta: N1 })
  const sonra = terminalReducer(yarim, { tip: 'DILIM_SEC', dilim: 'haftalik' })
  assert.equal(sonra.dilim, 'haftalik')
  assert.deepEqual(sonra.bekleyenNoktalar, [])
  assert.equal(terminalReducer(sonra, { tip: 'DILIM_SEC', dilim: 'haftalik' }), sonra)
})

test('GOSTERGE_DEGISTIR açar, ikinci çağrı kapatır', () => {
  const acik = terminalReducer(bosTerminalDurum(), { tip: 'GOSTERGE_DEGISTIR', kimlik: 'rsi14' })
  assert.deepEqual(acik.gostergeler, ['rsi14'])
  const kapali = terminalReducer(acik, { tip: 'GOSTERGE_DEGISTIR', kimlik: 'rsi14' })
  assert.deepEqual(kapali.gostergeler, [])
})

test('gösterge sırası KANONİKTİR — açma sırasına göre değişmez', () => {
  // Tıklama sırası tersten: önce macd, sonra sma20.
  const bir = terminalReducer(bosTerminalDurum(), { tip: 'GOSTERGE_DEGISTIR', kimlik: 'macd' })
  const iki = terminalReducer(bir, { tip: 'GOSTERGE_DEGISTIR', kimlik: 'sma20' })
  const kanonik = tumGostergeKimlikleri().filter((k) => k === 'sma20' || k === 'macd')
  assert.deepEqual(iki.gostergeler, kanonik)
  assert.deepEqual(iki.gostergeler, ['sma20', 'macd'])
})

test('NOKTA_EKLE imleç aracındayken YOK SAYILIR', () => {
  const bos = bosTerminalDurum()
  assert.equal(terminalReducer(bos, { tip: 'NOKTA_EKLE', nokta: N1 }), bos)
})

test('NOKTA_EKLE sonlu olmayan noktayı REDDEDER (Y3)', () => {
  const bir = aracli('trend')
  for (const bozuk of [
    { t_utc: Number.NaN, fiyat: 100 },
    { t_utc: 1, fiyat: Number.POSITIVE_INFINITY },
  ]) {
    assert.equal(terminalReducer(bir, { tip: 'NOKTA_EKLE', nokta: bozuk }), bir)
  }
})

test('NOKTA_EKLE gerekli sayının ÜSTÜNE nokta biriktirmez', () => {
  let durum = aracli('trend') // trend = 2 nokta
  durum = terminalReducer(durum, { tip: 'NOKTA_EKLE', nokta: N1 })
  durum = terminalReducer(durum, { tip: 'NOKTA_EKLE', nokta: N2 })
  const dolu = durum
  assert.equal(dolu.bekleyenNoktalar.length, 2)
  assert.equal(terminalReducer(dolu, { tip: 'NOKTA_EKLE', nokta: N1 }), dolu)
})

test('CIZIM_IPTAL bekleyen noktaları siler, aracı korur; boşken etkisizdir', () => {
  const bir = aracli('dikdortgen')
  const yarim = terminalReducer(bir, { tip: 'NOKTA_EKLE', nokta: N1 })
  const iptal = terminalReducer(yarim, { tip: 'CIZIM_IPTAL' })
  assert.deepEqual(iptal.bekleyenNoktalar, [])
  assert.equal(iptal.arac, 'dikdortgen')
  assert.equal(terminalReducer(iptal, { tip: 'CIZIM_IPTAL' }), iptal)
})

test('reducer GİRDİ durumunu mutasyona uğratmaz', () => {
  const bir = aracli('trend')
  const anlik = JSON.stringify(bir)
  terminalReducer(bir, { tip: 'NOKTA_EKLE', nokta: N1 })
  terminalReducer(bir, { tip: 'GOSTERGE_DEGISTIR', kimlik: 'ema20' })
  terminalReducer(bir, { tip: 'DILIM_SEC', dilim: 'aylik' })
  assert.equal(JSON.stringify(bir), anlik)
})

test('tiklamaSonucu: TEK noktalı araç ilk tıklamada çizimi tamamlar', () => {
  const sonuc = tiklamaSonucu(aracli('yatay'), N1, KIMLIK)
  assert.ok(sonuc.tamamlananCizim)
  assert.equal(sonuc.tamamlananCizim.tip, 'yatay')
  assert.equal(gecerliCizim(sonuc.tamamlananCizim), true)
  assert.deepEqual(sonuc.yeniDurum.bekleyenNoktalar, [])
  assert.equal(sonuc.hata, undefined)
})

test('tiklamaSonucu: İKİ noktalı araç ikinci tıklamada tamamlanır, sıra korunur', () => {
  const ilk = tiklamaSonucu(aracli('trend'), N1, KIMLIK)
  assert.equal(ilk.tamamlananCizim, undefined)
  assert.deepEqual(ilk.yeniDurum.bekleyenNoktalar, [N1])

  const ikinci = tiklamaSonucu(ilk.yeniDurum, N2, KIMLIK)
  assert.ok(ikinci.tamamlananCizim)
  assert.deepEqual(ikinci.tamamlananCizim.noktalar, [N1, N2])
  assert.deepEqual(ikinci.yeniDurum.bekleyenNoktalar, [])
})

test('tiklamaSonucu: çizim bitince ARAÇ SEÇİLİ KALIR (arka arkaya çizim)', () => {
  const sonuc = tiklamaSonucu(aracli('olcum'), N1, KIMLIK)
  const ikinci = tiklamaSonucu(sonuc.yeniDurum, N2, { ...KIMLIK, id: 'c-2' })
  assert.equal(ikinci.yeniDurum.arac, 'olcum')
  assert.ok(ikinci.tamamlananCizim)
})

test('tiklamaSonucu: id ve olusturma_utc DIŞARIDAN gelir (saflık)', () => {
  const sonuc = tiklamaSonucu(aracli('dikey'), N1, KIMLIK)
  assert.ok(sonuc.tamamlananCizim)
  assert.equal(sonuc.tamamlananCizim.id, KIMLIK.id)
  assert.equal(sonuc.tamamlananCizim.olusturma_utc, KIMLIK.olusturma_utc)
  // İki kez çağrıldığında aynı çıktı: içeride zaman/rastgelelik yok.
  assert.deepEqual(tiklamaSonucu(aracli('dikey'), N1, KIMLIK).tamamlananCizim, sonuc.tamamlananCizim)
})

test('tiklamaSonucu: imleç aracıyla tıklama çizim ÜRETMEZ, durumu değiştirmez', () => {
  const bos = bosTerminalDurum()
  const sonuc = tiklamaSonucu(bos, N1, KIMLIK)
  assert.equal(sonuc.yeniDurum, bos)
  assert.equal(sonuc.tamamlananCizim, undefined)
  assert.equal(sonuc.hata, undefined)
})

test('tiklamaSonucu: metin aracı METİNSİZ çizim üretmez ve SEBEBİ döner', () => {
  const sonuc = tiklamaSonucu(aracli('metin'), N1, KIMLIK)
  assert.equal(sonuc.tamamlananCizim, undefined)
  assert.equal(sonuc.hata, ARAYUZ_METINLERI.cizimGecersiz)
  // Yarım birikim ilerletilmez: durum girdiyle aynı kalır.
  assert.deepEqual(sonuc.yeniDurum.bekleyenNoktalar, [])
})

test('tiklamaSonucu: metin verilince metin çizimi geçerli üretilir', () => {
  const sonuc = tiklamaSonucu(aracli('metin'), N1, { ...KIMLIK, metin: 'SMA kesişimi' })
  assert.ok(sonuc.tamamlananCizim)
  assert.equal(sonuc.tamamlananCizim.metin, 'SMA kesişimi')
  assert.equal(gecerliCizim(sonuc.tamamlananCizim), true)
})

test('tiklamaSonucu: bozuk stil çizimi ENGELLER (şema kapısı gerçekten çalışıyor)', () => {
  const bozukStil = { ...KIMLIK, stil: { renk: '', kalinlik: 0 } }
  const sonuc = tiklamaSonucu(aracli('yatay'), N1, bozukStil)
  assert.equal(sonuc.tamamlananCizim, undefined)
  assert.equal(sonuc.hata, ARAYUZ_METINLERI.cizimGecersiz)
})

test('tiklamaSonucu: hesaplanamayan nokta için GÖRÜNÜR sebep döner (sessizlik yok)', () => {
  const bir = aracli('trend')
  const sonuc = tiklamaSonucu(bir, { t_utc: Number.NaN, fiyat: 100 }, KIMLIK)
  assert.equal(sonuc.yeniDurum, bir)
  assert.equal(sonuc.hata, ARAYUZ_METINLERI.noktaHesaplanamadi)
})

test('dilimEtiketi: türetilmemiş veri AÇIKÇA "türetilmedi" der', () => {
  const etiket = dilimEtiketi('gunluk', false, false)
  assert.ok(etiket.startsWith(DILIM_ETIKETLERI.gunluk))
  assert.match(etiket, /türetilmedi/)
  assert.doesNotMatch(etiket, /henüz tamamlanmadı/)
})

test('dilimEtiketi: türetilmiş veri ve EKSİK son kova ayrı ayrı görünür', () => {
  const tam = dilimEtiketi('haftalik', true, false)
  assert.ok(tam.startsWith(DILIM_ETIKETLERI.haftalik))
  assert.match(tam, /türetildi/)
  assert.doesNotMatch(tam, /henüz tamamlanmadı/)

  const eksik = dilimEtiketi('aylik', true, true)
  assert.match(eksik, /türetildi/)
  assert.match(eksik, /henüz tamamlanmadı/)
})

test('GUN_ICI_DILIMLER dolu ve sebebi tarifsel — düğmeler devre dışı gerekçeli', () => {
  assert.ok(GUN_ICI_DILIMLER.length >= 3)
  assert.match(gunIciNeden(), /veri kaynağı yok/)
  // Gün içi dilimler DESTEKLENEN dilim listesine sızmamalı.
  for (const dilim of DILIM_SIRASI) {
    assert.equal(GUN_ICI_DILIMLER.includes(dilim), false)
  }
  assert.deepEqual(DILIM_SIRASI, ['gunluk', 'haftalik', 'aylik'])
})

test('veriNotu: atlanan yoksa null, varsa SAYIYI yazar (sessiz kayıp yok)', () => {
  assert.equal(veriNotu(0, 0), null)
  assert.match(String(veriNotu(3, 0)), /3 kayıt/)
  assert.match(String(veriNotu(0, 2)), /2 bar/)
  const ikisi = String(veriNotu(3, 2))
  assert.match(ikisi, /3 kayıt/)
  assert.match(ikisi, /2 bar/)
})

// Y8 HUKUKİ DİL KAPISI — arayüzde GÖRÜNEN her metin tarifsel olmak zorunda.
// Kalıplar hukuki_dil.py'deki listeden TÜRETİLDİ (kopyalanmadı); kaynak dosya
// başka bir depodadır ve buradan çağrılamaz.
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
]

/** Arayüzde görünebilecek TÜM sabit metinler tek listede toplanır. */
function tumArayuzMetinleri(): string[] {
  const metinler: string[] = [
    ...Object.values(ARAYUZ_METINLERI),
    ...Object.values(ARAC_ETIKETLERI),
    ...Object.values(DILIM_ETIKETLERI),
    ...GUN_ICI_DILIMLER,
    gunIciNeden(),
    String(veriNotu(3, 2)),
    kayitHataMetni('cizim', { basarili: false, kotaDoldu: true, hata: 'x' }),
    kayitHataMetni('gosterge', { basarili: false, kotaDoldu: true, hata: 'x' }),
    String(yuklemeNotu('bozuk kayit sifirlandi', 'bilinmeyen surum (v=9) sifirlandi')),
  ]
  for (const dilim of DILIM_SIRASI) {
    for (const turetildi of [false, true]) {
      for (const eksik of [false, true]) {
        metinler.push(dilimEtiketi(dilim, turetildi, eksik))
      }
    }
  }
  return metinler
}

test('Y8: bileşenin gösterdiği tüm sabit metinler yasaklı kalıplara takılmaz', () => {
  const metinler = tumArayuzMetinleri()
  // Liste boşalırsa test "geçer" görünürdü; alt sınır bunu imkânsız kılar.
  assert.ok(metinler.length >= 40, `metin sayısı beklenenden az: ${metinler.length}`)
  for (const metin of metinler) {
    for (const { ad, kalip } of YASAKLI_KALIPLAR) {
      assert.equal(kalip.test(metin), false, `"${metin}" metni "${ad}" kalıbına takıldı`)
    }
  }
})

test('Y8 kapısı gerçekten çalışıyor: yasaklı bir metin ELENİR', () => {
  // Kapının kendisi sınanmazsa, hiçbiri eşleşmeyen bir regex listesi de "geçer".
  const ornekler = ['Şimdi almalısınız', 'Geri al', 'risksiz kazanç', 'hedef fiyat 120', 'SAT']
  for (const ornek of ornekler) {
    assert.equal(
      YASAKLI_KALIPLAR.some(({ kalip }) => kalip.test(ornek)),
      true,
      `"${ornek}" yakalanmalıydı`,
    )
  }
})

test('B4 REGRESYON: klavye ipucu YIKICI tuşların HEPSİNİ söyler', () => {
  // Bileşen hem Delete hem Backspace ile siliyor; ipucu yalnızca Delete
  // diyordu. Belgelenmemiş yıkıcı tuş, kullanıcının veri kaybetmesidir.
  assert.match(ARAYUZ_METINLERI.klavyeIpucu, /Delete/)
  assert.match(ARAYUZ_METINLERI.klavyeIpucu, /Backspace/)
  assert.match(ARAYUZ_METINLERI.klavyeIpucu, /Escape/)
})

// ---------------------------------------------------------------- KALICILIK (ADR-5)

test('GOSTERGELERI_YUKLE kayıtlı seçimi uygular; araç/dilim/yarım çizime DOKUNMAZ', () => {
  const baslangic: TerminalDurum = { ...aracli('trend'), dilim: 'haftalik', bekleyenNoktalar: [N1] }
  const sonuc = terminalReducer(baslangic, { tip: 'GOSTERGELERI_YUKLE', gostergeler: ['rsi14', 'sma20'] })
  // Kanonik sıra: yüklenen sıra değil, tumGostergeKimlikleri sırası (alt panel yerleri sabit kalsın).
  assert.deepEqual(sonuc.gostergeler, ['sma20', 'rsi14'])
  assert.equal(sonuc.arac, 'trend')
  assert.equal(sonuc.dilim, 'haftalik')
  assert.deepEqual(sonuc.bekleyenNoktalar, [N1])
})

test('GOSTERGELERI_YUKLE önceki seçimin YERİNE geçer (sembol değişimi birikmez)', () => {
  const aapl = terminalReducer(bosTerminalDurum(), { tip: 'GOSTERGELERI_YUKLE', gostergeler: ['macd'] })
  const tsla = terminalReducer(aapl, { tip: 'GOSTERGELERI_YUKLE', gostergeler: [] })
  assert.deepEqual(tsla.gostergeler, [])
})

test('GOSTERGELERI_YUKLE aynı içerikte girdi durumunun KENDİSİNİ döndürür', () => {
  const durum = terminalReducer(bosTerminalDurum(), { tip: 'GOSTERGELERI_YUKLE', gostergeler: ['ema20'] })
  // Referans eşitliği: gereksiz render ve gereksiz kayıt tetiklenmez.
  assert.equal(terminalReducer(durum, { tip: 'GOSTERGELERI_YUKLE', gostergeler: ['ema20'] }), durum)
})

test('yuklemeNotu: uyarı yoksa null, varsa hangi kayda ait olduğu önekle yazılır', () => {
  assert.equal(yuklemeNotu(undefined, undefined), null)
  assert.equal(yuklemeNotu('', undefined), null)
  assert.equal(yuklemeNotu('bozuk kayit sifirlandi', undefined), 'Kayıtlı çizimler: bozuk kayit sifirlandi')
  assert.equal(
    yuklemeNotu(undefined, 'bilinmeyen surum (v=9) sifirlandi'),
    'Kayıtlı göstergeler: bilinmeyen surum (v=9) sifirlandi',
  )
  const ikisi = String(yuklemeNotu('a', 'b'))
  assert.match(ikisi, /Kayıtlı çizimler: a/)
  assert.match(ikisi, /Kayıtlı göstergeler: b/)
})

test('kayitHataMetni (Y9): başarıda boş; kota dolunca teknik değil ANLAŞILIR metin', () => {
  assert.equal(kayitHataMetni('cizim', { basarili: true }), '')
  const kota = kayitHataMetni('gosterge', { basarili: false, kotaDoldu: true, hata: 'kaydedilemedi: QuotaExceededError: x' })
  assert.match(kota, /^Gösterge seçimi tarayıcı deposuna yazılamadı: /)
  assert.match(kota, /dolu/)
  assert.match(kota, /yenilenirse/) // sonuç: yenileyince kaybolacağı söylenir
  assert.doesNotMatch(kota, /QuotaExceededError/)
  // Kota dışı hata: teknik ayrıntı saklanmaz (tanı için gerekli).
  assert.equal(
    kayitHataMetni('cizim', { basarili: false, hata: 'kaydedilemedi: SecurityError: y' }),
    'Çizimler tarayıcı deposuna yazılamadı: kaydedilemedi: SecurityError: y',
  )
})
