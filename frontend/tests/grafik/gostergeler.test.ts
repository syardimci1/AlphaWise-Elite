// Kategori: GRAFIK GOSTERGELERI - saflik, isinma hizalamasi ve TA-Lib referansi.
//
// REFERANS URETIMI (salt-okunur, konteynerdeki korunan dosyalara dokunulmadi):
//   docker exec -i alphawise-taa python3 -   # asagidaki betik stdin'den verildi
//     import math, numpy as np, talib
//     seri = [round(100 + 10*math.sin(i/3.0) + 0.5*i, 2) for i in range(60)]
//     a = np.array(seri, dtype=float)
//     talib.SMA(a,5); talib.SMA(a,20); talib.EMA(a,5); talib.EMA(a,20)
//     talib.RSI(a,14); talib.BBANDS(a,20,2.0,2.0,matype=0); talib.MACD(a,12,26,9)
// TA-Lib surumu 0.7.0, numpy 2.5.3. NaN olan isinma indeksleri atildi, kalan
// kuyruk 8 basamaga yuvarlanarak asagiya SABIT olarak gomuldu.
// TOLERANS: 1e-6 (mutlak). Yuvarlamanin kattigi hata <= 5e-9, paydan kucuk.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { sma, ema, bollinger, rsi, macd } from '../../src/lib/grafik/gostergeler'

const TOLERANS = 1e-6

const SERI: number[] = [
  100.0, 103.77, 107.18, 109.91, 111.72, 112.45,
  112.09, 110.73, 108.57, 105.91, 103.09, 100.49,
  98.43, 97.21, 97.01, 97.91, 99.87, 102.72,
  106.21, 110.0, 113.74, 117.07, 119.67, 121.33,
  121.89, 121.37, 119.88, 117.62, 114.91, 112.1,
  109.56, 107.61, 106.54, 106.5, 107.57, 109.67,
  112.63, 116.19, 120.0, 123.7, 126.94, 129.41,
  130.91, 131.31, 130.63, 129.0, 126.66, 123.91,
  121.12, 118.65, 116.82, 115.89, 116.01, 117.24,
  119.49, 122.56, 126.18, 130.0, 133.65, 136.79,
]

// talib.SMA(seri, 5)
const REF_SMA5_BAS = 4
const REF_SMA5: number[] = [
  106.516, 109.006, 110.67, 111.38,
  111.112, 109.95, 108.078, 105.758,
  103.298, 101.026, 99.246, 98.21,
  98.086, 98.944, 100.744, 103.342,
  106.508, 109.948, 113.338, 116.362,
  118.74, 120.266, 120.828, 120.418,
  119.134, 117.176, 114.814, 112.36,
  110.144, 108.462, 107.556, 107.578,
  108.582, 110.512, 113.212, 116.438,
  119.892, 123.248, 126.192, 128.454,
  129.84, 130.252, 129.702, 128.302,
  126.264, 123.868, 121.432, 119.278,
  117.698, 116.922, 117.09, 118.238,
  120.296, 123.094, 126.376, 129.836,
]

// talib.SMA(seri, 20)
const REF_SMA20_BAS = 19
const REF_SMA20: number[] = [
  104.7635, 105.4505, 106.1155, 106.74,
  107.311, 107.8195, 108.2655, 108.655,
  108.9995, 109.3165, 109.626, 109.9495,
  110.3055, 110.711, 111.1755, 111.7035,
  112.2915, 112.9295, 113.603, 114.2925,
  114.9775, 115.6375, 116.2545, 116.8165,
  117.3155, 117.7525, 118.134, 118.473,
  118.7875, 119.098, 119.4255, 119.7885,
  120.2025, 120.676, 121.213, 121.809,
  122.4535, 123.131, 123.8215, 124.504,
  125.1585,
]

// talib.EMA(seri, 5)
const REF_EMA5_BAS = 4
const REF_EMA5: number[] = [
  106.516, 108.494, 109.69266667, 110.03844444,
  109.54896296, 108.33597531, 106.58731687, 104.55487791,
  102.51325194, 100.7455013, 99.5003342, 98.9702228,
  99.27014853, 100.42009902, 102.35006601, 104.90004401,
  107.84669601, 110.92113067, 113.83742045, 116.33494696,
  118.18663131, 119.24775421, 119.4585028, 118.84566854,
  117.53377902, 115.72251935, 113.66834623, 111.64889749,
  109.94593166, 108.79728777, 108.38819185, 108.81546123,
  110.08697415, 112.1213161, 114.74754407, 117.73169605,
  120.8011307, 123.6707538, 126.08383587, 127.82589058,
  128.76059372, 128.84039581, 128.11359721, 126.71239814,
  124.84826543, 122.78217695, 120.79478463, 119.15985642,
  118.10990428, 117.81993619, 118.37662413, 119.77108275,
  121.9073885, 124.60492567, 127.61995044, 130.67663363,
]

// talib.EMA(seri, 20)
const REF_EMA20_BAS = 19
const REF_EMA20: number[] = [
  104.7635, 105.61840476, 106.70903288, 107.9434107,
  109.21832397, 110.42515026, 111.4675169, 112.26870577,
  112.77835284, 112.98136685, 112.89742715, 112.57957695,
  112.1062839, 111.57616163, 111.09271766, 110.75722074,
  110.65367591, 110.84189725, 111.35124037, 112.17493176,
  113.27255731, 114.57421852, 115.98715009, 117.40837389,
  118.73233828, 119.86544892, 120.73540617, 121.2996532,
  121.54825766, 121.50747121, 121.2353311, 120.81482337,
  120.34579258, 119.93285995, 119.6763971, 119.65864499,
  119.93496452, 120.5297298, 121.4316603, 122.5953117,
  123.94718677,
]

// talib.RSI(seri, 14)
const REF_RSI14_BAS = 14
const REF_RSI14: number[] = [
  44.63965579, 46.49892049, 50.40531268, 55.49399546,
  60.79842827, 65.59412215, 69.55249549, 72.5776408,
  74.69194334, 75.96605309, 76.39773743, 75.04973595,
  71.17446821, 65.63821247, 59.64685794, 54.12958253,
  49.65821586, 46.48360165, 44.7914893, 44.72594275,
  46.96183704, 51.13927518, 56.35712963, 61.66017296,
  66.36993758, 70.1986006, 73.0879149, 75.07209266,
  76.21878336, 76.52884521, 74.74470771, 70.50177089,
  64.81368956, 58.80874249, 53.40289902, 49.09982378,
  46.13381587, 44.65742093, 44.90243923, 47.46962999,
  51.8859429, 57.17618202, 62.42283365, 67.0153267,
  70.700055, 73.44802267,
]

// talib.BBANDS(seri, 20, 2.0, 2.0, matype=0) -> orta
const REF_BB_ORTA_BAS = 19
const REF_BB_ORTA: number[] = [
  104.7635, 105.4505, 106.1155, 106.74,
  107.311, 107.8195, 108.2655, 108.655,
  108.9995, 109.3165, 109.626, 109.9495,
  110.3055, 110.711, 111.1755, 111.7035,
  112.2915, 112.9295, 113.603, 114.2925,
  114.9775, 115.6375, 116.2545, 116.8165,
  117.3155, 117.7525, 118.134, 118.473,
  118.7875, 119.098, 119.4255, 119.7885,
  120.2025, 120.676, 121.213, 121.809,
  122.4535, 123.131, 123.8215, 124.504,
  125.1585,
]

// talib.BBANDS(...) -> ust
const REF_BB_UST_BAS = 19
const REF_BB_UST: number[] = [
  115.26601832, 116.40460147, 118.14301757, 120.14221773,
  122.10556373, 123.83406896, 125.23917547, 126.30585777,
  127.06303174, 127.56037927, 127.83821283, 127.91399551,
  127.78160881, 127.4258723, 126.84760959, 126.08986615,
  125.26684011, 124.58692077, 124.34359793, 124.81446916,
  126.0612735, 127.86131426, 129.87157821, 131.80933332,
  133.49347945, 134.84732714, 135.86349339, 136.57836064,
  137.04058508, 137.28784838, 137.33324411, 137.16815279,
  136.77788039, 136.16887113, 135.39203396, 134.5758162,
  133.94139846, 133.78993597, 134.38118233, 135.73087739,
  137.5838439,
]

// talib.BBANDS(...) -> alt
const REF_BB_ALT_BAS = 19
const REF_BB_ALT: number[] = [
  94.26098168, 94.49639853, 94.08798243, 93.33778227,
  92.51643627, 91.80493104, 91.29182453, 91.00414223,
  90.93596826, 91.07262073, 91.41378717, 91.98500449,
  92.82939119, 93.9961277, 95.50339041, 97.31713385,
  99.31615989, 101.27207923, 102.86240207, 103.77053084,
  103.8937265, 103.41368574, 102.63742179, 101.82366668,
  101.13752055, 100.65767286, 100.40450661, 100.36763936,
  100.53441492, 100.90815162, 101.51775589, 102.40884721,
  103.62711961, 105.18312887, 107.03396604, 109.0421838,
  110.96560154, 112.47206403, 113.26181767, 113.27712261,
  112.7331561,
]

// talib.MACD(seri, 12, 26, 9) -> macd
const REF_MACD_BAS = 33
const REF_MACD: number[] = [
  0.85647544, 0.57565946, 0.51660808, 0.70058084,
  1.12072382, 1.74105551, 2.50238598, 3.32881428,
  4.13540267, 4.83987617, 5.36856764, 5.66735933,
  5.70684161, 5.48607312, 5.03121378, 4.39494263,
  3.64931774, 2.87756812, 2.16594015, 1.59328644,
  1.22458867, 1.10125466, 1.23697581, 1.61798839,
  2.20279325, 2.92703873, 3.71159529,
]

// talib.MACD(...) -> sinyal
const REF_MACD_SINYAL_BAS = 33
const REF_MACD_SINYAL: number[] = [
  2.43386881, 2.06222694, 1.75310317, 1.5425987,
  1.45822373, 1.51479008, 1.71230926, 2.03561026,
  2.45556875, 2.93243023, 3.41965771, 3.86919804,
  4.23672675, 4.48659602, 4.59551957, 4.55540419,
  4.3741869, 4.07486314, 3.69307854, 3.27312012,
  2.86341383, 2.510982, 2.25618076, 2.12854229,
  2.14339248, 2.30012173, 2.58241644,
]

// talib.MACD(...) -> histogram
const REF_MACD_HIST_BAS = 33
const REF_MACD_HIST: number[] = [
  -1.57739336, -1.48656748, -1.23649509, -0.84201786,
  -0.33749991, 0.22626543, 0.79007672, 1.29320401,
  1.67983393, 1.90744594, 1.94890993, 1.7981613,
  1.47011486, 0.99947709, 0.4356942, -0.16046156,
  -0.72486916, -1.19729502, -1.52713839, -1.67983368,
  -1.63882516, -1.40972734, -1.01920495, -0.51055389,
  0.05940077, 0.626917, 1.12917885,
]


// --- yardimcilar -----------------------------------------------------------

/** null cikarsa testi anlasilir bir mesajla dusurur; TS daraltmasina guvenmez. */
function sayi(deger: number | null, ad: string, indeks: number): number {
  if (deger === null) throw new Error(`${ad}[${indeks}] null geldi; dolu olmasi bekleniyordu`)
  return deger
}

function yakin(uretilen: number, beklenen: number, ad: string, indeks: number): void {
  const fark = Math.abs(uretilen - beklenen)
  assert.ok(
    fark <= TOLERANS,
    `${ad}[${indeks}]: ${uretilen} != ${beklenen} (fark ${fark}, tolerans ${TOLERANS})`,
  )
}

/** Isinma bolgesinin tamamen null, kalanin referansa esit oldugunu dogrular. */
function referansDogrula(
  ad: string,
  uretilen: (number | null)[],
  bas: number,
  referans: number[],
): void {
  assert.equal(uretilen.length, SERI.length, `${ad}: cikti uzunlugu girdiyle ayni olmali`)
  assert.equal(referans.length, SERI.length - bas, `${ad}: referans kuyrugu beklenen uzunlukta degil`)
  for (let i = 0; i < bas; i++) {
    assert.equal(uretilen[i], null, `${ad}: isinma indeksi ${i} null olmaliydi`)
  }
  for (let j = 0; j < referans.length; j++) {
    const i = bas + j
    yakin(sayi(uretilen[i], ad, i), referans[j], ad, i)
  }
}

function tumuNullMu(seri: (number | null)[], beklenenUzunluk: number, ad: string): void {
  assert.equal(seri.length, beklenenUzunluk, `${ad}: uzunluk girdiyle ayni olmali`)
  for (let i = 0; i < seri.length; i++) {
    assert.equal(seri[i], null, `${ad}: ${i} null olmaliydi`)
  }
}

// --- SMA -------------------------------------------------------------------

test('SMA: isinma null, hizalama korunur, degerler elle dogrulanabilir', () => {
  const girdi = [1, 2, 3, 4, 5, 6]
  const cikti = sma(girdi, 3)
  assert.equal(cikti.length, girdi.length)
  assert.equal(cikti[0], null)
  assert.equal(cikti[1], null)
  assert.equal(cikti[2], 2) // (1+2+3)/3
  assert.equal(cikti[3], 3)
  assert.equal(cikti[4], 4)
  assert.equal(cikti[5], 5)
})

test('SMA: uc durumlar (bos, tek eleman, pencere<1, pencere>uzunluk) patlamaz', () => {
  assert.deepEqual(sma([], 5), [])
  tumuNullMu(sma([42], 5), 1, 'sma(tek eleman, 5)')
  assert.deepEqual(sma([42], 1), [42])
  tumuNullMu(sma([1, 2, 3], 0), 3, 'sma(pencere=0)')
  tumuNullMu(sma([1, 2, 3], -2), 3, 'sma(pencere=-2)')
  tumuNullMu(sma([1, 2, 3], 4), 3, 'sma(pencere>uzunluk)')
})

test('SMA: TA-Lib referansi (pencere 5 ve 20)', () => {
  referansDogrula('sma5', sma(SERI, 5), REF_SMA5_BAS, REF_SMA5)
  referansDogrula('sma20', sma(SERI, 20), REF_SMA20_BAS, REF_SMA20)
})

// --- EMA -------------------------------------------------------------------

test('EMA: ilk dolu indeks pencere-1 ve tohum SMA ile birebir ayni', () => {
  const e = ema(SERI, 5)
  const s = sma(SERI, 5)
  assert.equal(e.length, SERI.length)
  for (let i = 0; i < 4; i++) assert.equal(e[i], null, `ema isinma ${i}`)
  // TOHUM SECIMI kaniti: ilk dolu EMA degeri, ayni pencerenin basit ortalamasi.
  assert.equal(sayi(e[4], 'ema5', 4), sayi(s[4], 'sma5', 4))
})

test('EMA: uc durumlar (bos, pencere<1, pencere>uzunluk) patlamaz', () => {
  assert.deepEqual(ema([], 5), [])
  tumuNullMu(ema([1, 2, 3], 0), 3, 'ema(pencere=0)')
  tumuNullMu(ema([1, 2, 3], 9), 3, 'ema(pencere>uzunluk)')
  assert.deepEqual(ema([7], 1), [7])
})

test('EMA: TA-Lib referansi (pencere 5 ve 20)', () => {
  referansDogrula('ema5', ema(SERI, 5), REF_EMA5_BAS, REF_EMA5)
  referansDogrula('ema20', ema(SERI, 20), REF_EMA20_BAS, REF_EMA20)
})

// --- BOLLINGER -------------------------------------------------------------

test('BOLLINGER: orta bant SMA ile ayni, bantlar ortaya gore simetrik', () => {
  const b = bollinger(SERI, 20, 2)
  const s = sma(SERI, 20)
  assert.equal(b.orta.length, SERI.length)
  assert.equal(b.ust.length, SERI.length)
  assert.equal(b.alt.length, SERI.length)
  for (let i = 0; i < SERI.length; i++) {
    assert.equal(b.orta[i], s[i], `orta[${i}] sma ile ayni olmali`)
    if (b.orta[i] === null) {
      assert.equal(b.ust[i], null)
      assert.equal(b.alt[i], null)
      continue
    }
    const orta = sayi(b.orta[i], 'orta', i)
    const ust = sayi(b.ust[i], 'ust', i)
    const alt = sayi(b.alt[i], 'alt', i)
    assert.ok(ust >= orta && orta >= alt, `bant sirasi bozuk: ${alt} <= ${orta} <= ${ust}`)
    yakin(ust - orta, orta - alt, 'bant simetrisi', i)
  }
})

test('BOLLINGER: sabit seride sapma 0, katsayi 0 iken uc bant cakisir', () => {
  const sabit = new Array<number>(10).fill(50)
  const b = bollinger(sabit, 5, 2)
  for (let i = 4; i < 10; i++) {
    assert.equal(sayi(b.ust[i], 'ust', i), 50)
    assert.equal(sayi(b.alt[i], 'alt', i), 50)
  }
  const k0 = bollinger(SERI, 20, 0)
  for (let i = 19; i < SERI.length; i++) {
    assert.equal(sayi(k0.ust[i], 'ust', i), sayi(k0.orta[i], 'orta', i))
    assert.equal(sayi(k0.alt[i], 'alt', i), sayi(k0.orta[i], 'orta', i))
  }
})

test('BOLLINGER: uc durumlar (bos, pencere>uzunluk, pencere<1) patlamaz', () => {
  const bos = bollinger([], 20, 2)
  assert.deepEqual(bos.orta, [])
  assert.deepEqual(bos.ust, [])
  assert.deepEqual(bos.alt, [])
  const kisa = bollinger([1, 2, 3], 20, 2)
  tumuNullMu(kisa.orta, 3, 'bollinger.orta(pencere>uzunluk)')
  tumuNullMu(kisa.ust, 3, 'bollinger.ust(pencere>uzunluk)')
  tumuNullMu(kisa.alt, 3, 'bollinger.alt(pencere>uzunluk)')
  const sifir = bollinger([1, 2, 3], 0, 2)
  tumuNullMu(sifir.ust, 3, 'bollinger.ust(pencere=0)')
})

test('BOLLINGER: TA-Lib referansi (pencere 20, katsayi 2.0, populasyon sapmasi)', () => {
  const b = bollinger(SERI, 20, 2)
  referansDogrula('bb.orta', b.orta, REF_BB_ORTA_BAS, REF_BB_ORTA)
  referansDogrula('bb.ust', b.ust, REF_BB_UST_BAS, REF_BB_UST)
  referansDogrula('bb.alt', b.alt, REF_BB_ALT_BAS, REF_BB_ALT)
})

// --- RSI -------------------------------------------------------------------

test('RSI: ilk dolu indeks `pencere` (pencere-1 DEGIL) ve tohum basit ortalama', () => {
  // 15 fiyat -> 14 fark; pencere 14 icin ilk RSI tam olarak 14. indekste.
  const girdi = [10, 11, 10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16]
  const r = rsi(girdi, 14)
  assert.equal(r.length, girdi.length)
  for (let i = 0; i < 14; i++) assert.equal(r[i], null, `rsi isinma ${i}`)
  // Tohum elle: kazanclar 1,2,2,2,2,2,2 = 13/14; kayiplar 1,1,1,1,1,1,1 = 7/14
  const beklenen = (100 * (13 / 14)) / (13 / 14 + 7 / 14)
  yakin(sayi(r[14], 'rsi', 14), beklenen, 'rsi tohum', 14)
})

test('RSI: monoton artan 100, monoton azalan 0, tamamen duz 0 doner', () => {
  const artan = Array.from({ length: 20 }, (_unused, i) => 100 + i)
  const azalan = Array.from({ length: 20 }, (_unused, i) => 200 - i)
  const duz = new Array<number>(20).fill(100)
  // Bu uc deger TA-Lib ile olculdu (RSI(.,14) -> 100.0 / 0.0 / 0.0), varsayilmadi.
  for (let i = 14; i < 20; i++) {
    assert.equal(sayi(rsi(artan, 14)[i], 'rsi artan', i), 100)
    assert.equal(sayi(rsi(azalan, 14)[i], 'rsi azalan', i), 0)
    assert.equal(sayi(rsi(duz, 14)[i], 'rsi duz', i), 0)
  }
})

test('RSI: uc durumlar - uzunluk <= pencere ise tamami null, patlamaz', () => {
  assert.deepEqual(rsi([], 14), [])
  tumuNullMu(rsi([1, 2, 3], 14), 3, 'rsi(pencere>uzunluk)')
  // 14 fiyat = 13 fark: 14 pencerelik RSI icin YETERSIZ, hepsi null olmali.
  tumuNullMu(rsi(SERI.slice(0, 14), 14), 14, 'rsi(tam sinirin bir altinda)')
  tumuNullMu(rsi([1, 2, 3], 0), 3, 'rsi(pencere=0)')
  tumuNullMu(rsi([5], 1), 1, 'rsi(tek eleman)')
})

test('RSI: TA-Lib referansi (Wilder, pencere 14)', () => {
  referansDogrula('rsi14', rsi(SERI, 14), REF_RSI14_BAS, REF_RSI14)
})

// --- MACD ------------------------------------------------------------------

test('MACD: hizalama - macd cizgisi yavas-1, sinyal/histogram (yavas-1)+(sinyal-1) indeksten', () => {
  const m = macd(SERI, 12, 26, 9)
  assert.equal(m.macd.length, SERI.length)
  assert.equal(m.sinyal.length, SERI.length)
  assert.equal(m.histogram.length, SERI.length)
  for (let i = 0; i < 25; i++) assert.equal(m.macd[i], null, `macd isinma ${i}`)
  for (let i = 0; i < 33; i++) {
    assert.equal(m.sinyal[i], null, `sinyal isinma ${i}`)
    assert.equal(m.histogram[i], null, `histogram isinma ${i}`)
  }
  // 25..32: TA-Lib bu araligi kirpar (uc ciktiya tek lookback uygular), biz
  // ayni ozyinelemeden gelen gercek degerleri veriyoruz - uydurma degil.
  for (let i = 25; i < 33; i++) {
    assert.ok(Number.isFinite(sayi(m.macd[i], 'macd', i)), `macd[${i}] sonlu olmali`)
  }
  for (let i = 33; i < SERI.length; i++) {
    yakin(
      sayi(m.histogram[i], 'histogram', i),
      sayi(m.macd[i], 'macd', i) - sayi(m.sinyal[i], 'sinyal', i),
      'histogram = macd - sinyal',
      i,
    )
  }
})

test('MACD: TA-Lib referansi (12/26/9) - 33. indeksten itibaren karsilastirilir', () => {
  const m = macd(SERI, 12, 26, 9)
  // TA-Lib uc ciktiyi da 33'ten verdigi icin karsilastirma araligi 33..59.
  // 25..32 araligi bir ustteki testte ayrica belgelenir.
  assert.equal(REF_MACD_BAS, 33)
  for (let j = 0; j < REF_MACD.length; j++) {
    const i = REF_MACD_BAS + j
    yakin(sayi(m.macd[i], 'macd', i), REF_MACD[j], 'macd', i)
  }
  referansDogrula('macd.sinyal', m.sinyal, REF_MACD_SINYAL_BAS, REF_MACD_SINYAL)
  referansDogrula('macd.histogram', m.histogram, REF_MACD_HIST_BAS, REF_MACD_HIST)
})

test('MACD: uc durumlar (bos, kisa girdi, pencere<1) patlamaz', () => {
  const bos = macd([], 12, 26, 9)
  assert.deepEqual(bos.macd, [])
  assert.deepEqual(bos.sinyal, [])
  assert.deepEqual(bos.histogram, [])
  const kisa = macd([1, 2, 3], 12, 26, 9)
  tumuNullMu(kisa.macd, 3, 'macd(kisa).macd')
  tumuNullMu(kisa.sinyal, 3, 'macd(kisa).sinyal')
  tumuNullMu(kisa.histogram, 3, 'macd(kisa).histogram')
  const gecersiz = macd(SERI, 0, 26, 9)
  tumuNullMu(gecersiz.macd, SERI.length, 'macd(hizli=0).macd')
  const sinyalsiz = macd(SERI, 12, 26, 0)
  tumuNullMu(sinyalsiz.sinyal, SERI.length, 'macd(sinyal=0).sinyal')
})

// --- SAFLIK ----------------------------------------------------------------

test('SAFLIK: girdi mutasyona ugramaz ve ayni girdi ayni ciktiyi verir', () => {
  const kopya = SERI.slice()
  const ilk = {
    sma: sma(SERI, 20),
    ema: ema(SERI, 20),
    bollinger: bollinger(SERI, 20, 2),
    rsi: rsi(SERI, 14),
    macd: macd(SERI, 12, 26, 9),
  }
  assert.deepEqual(SERI, kopya, 'girdi dizisi degistirilmis')
  const ikinci = {
    sma: sma(SERI, 20),
    ema: ema(SERI, 20),
    bollinger: bollinger(SERI, 20, 2),
    rsi: rsi(SERI, 14),
    macd: macd(SERI, 12, 26, 9),
  }
  assert.deepEqual(ikinci, ilk, 'ayni girdi farkli cikti uretti')
})

// =========================================================================
// REGRESYON — 23.09.2026 bağımsız doğrulamasında bulunan S3.
//
// Sözleşme "hesaplanamayan indeksler null döner, sahte değer ÜRETİLMEZ" diyor,
// ama NaN/Infinity özyinelemeyi kalıcı zehirliyor ve çıktıda YAYILIYORDU.
// Sinsi tarafı: JSON.stringify hem NaN'ı hem Infinity'yi `null` yazar — yani
// "ısınma penceresi" ile "hesap bozuldu" ağ üzerinden ayırt edilemiyordu.
// =========================================================================

test('S3 REGRESYON: NaN girdisi çıktıya SIZMAZ, tamamı null döner', () => {
  const bozuk = [1, NaN, 3, 4, 5]
  assert.deepEqual(sma(bozuk, 2), [null, null, null, null, null])
  assert.deepEqual(ema(bozuk, 2), [null, null, null, null, null])
  assert.deepEqual(rsi(bozuk, 2), [null, null, null, null, null])
  assert.deepEqual(bollinger(bozuk, 2, 2).ust, [null, null, null, null, null])
})

test('S3 REGRESYON: Infinity ve -Infinity de sızmaz', () => {
  for (const kotu of [Infinity, -Infinity]) {
    const bozuk = [1, kotu, 3, 4, 5]
    for (const seri of [sma(bozuk, 2), ema(bozuk, 2), rsi(bozuk, 2)]) {
      assert.ok(
        seri.every((v) => v === null),
        `${String(kotu)} için tamamı null olmalıydı: ${JSON.stringify(seri)}`,
      )
    }
  }
})

test('S3 REGRESYON: macd üç çıktısının hiçbirinde sonlu olmayan değer kalmaz', () => {
  const m = macd([1, NaN, 3, 4, 5, 6, 7, 8, 9, 10], 2, 3, 2)
  for (const [ad, seri] of Object.entries(m)) {
    assert.ok(
      seri.every((v: number | null) => v === null),
      `macd.${ad} temiz değil: ${JSON.stringify(seri)}`,
    )
  }
})

test('S3 REGRESYON: sonlu olmayan değer SONDA olsa bile tüm seri null olur', () => {
  // Kapı tek geçişli ön kontrol olduğu için konumdan bağımsızdır; bu test
  // "sadece baştaki NaN yakalanıyor" gibi yarım bir düzeltmeyi engeller.
  const seri = sma([1, 2, 3, 4, NaN], 2)
  assert.ok(seri.every((v) => v === null), JSON.stringify(seri))
})

test('S3 TERS KONTROL: sağlıklı girdide davranış DEĞİŞMEDİ', () => {
  // Kapı aşırıya kaçıp geçerli seriyi de null'lasaydı bu test kırmızıya dönerdi.
  assert.deepEqual(sma([1, 2, 3, 4, 5], 3), [null, null, 2, 3, 4])
  assert.deepEqual(ema([1, 2, 3, 4, 5], 3), [null, null, 2, 3, 4])
  assert.deepEqual(rsi([1, 2, 3, 4], 2), [null, null, 100, 100])
})
