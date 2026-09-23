// Grafik gosterge katmani - saf, deterministik teknik gosterge fonksiyonlari.
//
// SOZLESME (tum fonksiyonlar icin gecerli):
//  - SAFLIK: DOM yok, Date/Math.random yok, girdi dizisi MUTASYONA UGRAMAZ.
//    Ayni girdi her zaman ayni ciktiyi verir.
//  - HIZALAMA: donen dizinin uzunlugu HER ZAMAN girdinin uzunlugu kadardir.
//    Boylece i. bar ile i. gosterge degeri ayni indekste kalir; grafikte
//    kaymaya yol acan slice/offset isi cagiran tarafa birakilmaz.
//  - ISINMA: hesaplanamayan indeksler `null` doner. Sahte/uydurma baslangic
//    degeri URETILMEZ (Y3). Cagiran taraf null'i "veri yok" diye cizmelidir.
//  - UC DURUM: bos dizi, tek eleman, pencere < 1, pencere > uzunluk gibi
//    durumlar patlamaz; tamami null olan dogru uzunlukta bir dizi doner.
//  - SONLULUK (S3, 23.09.2026): girdide NaN ya da Infinity varsa cikti
//    TAMAMI null doner. ONCEDEN bu degerler ozyinelemeyi kalici zehirliyor ve
//    ciktida NaN/Infinity olarak YAYILIYORDU. Tehlikesi sessiz olmasiydi:
//    JSON.stringify ikisini de `null` yazar, yani "isinma penceresi" ile
//    "hesap bozuldu" ayirt edilemez hale gelirdi - tam olarak sozlesmenin
//    yasakladigi sahte deger (Y3). Tek gecisli bir on kontrol O(n)'dir ve
//    hesabin kendisinden ucuzdur.
//
// REFERANS: tum degerler TA-Lib 0.7.0 (alphawise-taa konteyneri) ile
// karsilastirilarak dogrulanmistir; tolerans 1e-6. Tohumlama secimleri
// asagida her fonksiyonun basinda tek tek yazilidir.
//
// KAPSAM DISI: VWAP yazilmadi. market-data-service yalnizca GUNLUK bar
// veriyor, gun ici hacim profili yok; gunluk barla hesaplanan "VWAP" yaniltici
// olur (ADR-3).

/** Girdiyle ayni uzunlukta, tamami null olan bir sonuc serisi uretir. */
/**
 * Girdinin TAMAMI sonlu mu? (S3 kapisi)
 *
 * Neden tek yerde: her gosterge ayni on kosula sahip ve kontrolun
 * kopyalanmasi, birinde unutulunca sessiz bir bosluk birakirdi.
 */
function tumuSonlu(degerler: number[]): boolean {
  return degerler.every((d) => Number.isFinite(d))
}

function bosSeri(uzunluk: number): (number | null)[] {
  return new Array<number | null>(uzunluk).fill(null)
}

/**
 * Belirtilen indekste tohumlanan ustel hareketli ortalama.
 *
 * `baslangic` ilk dolu cikti indeksidir; tohum, o indekste biten `pencere`
 * uzunlugundaki basit ortalamadir (TA-Lib "classic" davranisi). Sonrasi
 * klasik ozyineleme: deger = (fiyat - onceki) * k + onceki, k = 2/(pencere+1).
 *
 * Disa acilmiyor: yalnizca `ema` ve `macd` farkli tohum noktalari istedigi
 * icin ayrilmis bir yardimci (bkz. macd'deki ortak tohum notu).
 */
function emaTohumlu(
  degerler: number[],
  pencere: number,
  baslangic: number,
): (number | null)[] {
  const sonuc = bosSeri(degerler.length)
  // S3 kapisi burada duruyor cunku `ema` ve `macd` ikisi de bu yardimciya
  // deleger; tek kapi her iki cagriyi da kapsar. `bollinger` ise `sma`
  // uzerinden gecer, onun kapisi kendi icindedir.
  if (!tumuSonlu(degerler)) return sonuc
  if (pencere < 1 || baslangic >= degerler.length || baslangic - pencere + 1 < 0) {
    return sonuc
  }
  let tohum = 0
  for (let i = baslangic - pencere + 1; i <= baslangic; i++) {
    tohum += degerler[i]
  }
  let onceki = tohum / pencere
  sonuc[baslangic] = onceki
  const k = 2 / (pencere + 1)
  for (let i = baslangic + 1; i < degerler.length; i++) {
    onceki = (degerler[i] - onceki) * k + onceki
    sonuc[i] = onceki
  }
  return sonuc
}

/**
 * Basit hareketli ortalama. Ilk dolu indeks: pencere-1.
 *
 * Kayan toplam kullanir (O(n)); TA-Lib de ayni kayan toplami kullandigi icin
 * kayan nokta birikimi referansla ayni yonde ilerler.
 */
export function sma(degerler: number[], pencere: number): (number | null)[] {
  const sonuc = bosSeri(degerler.length)
  if (!tumuSonlu(degerler)) return sonuc
  if (pencere < 1 || pencere > degerler.length) return sonuc
  let toplam = 0
  for (let i = 0; i < degerler.length; i++) {
    toplam += degerler[i]
    if (i >= pencere) toplam -= degerler[i - pencere]
    if (i >= pencere - 1) sonuc[i] = toplam / pencere
  }
  return sonuc
}

/**
 * Ustel hareketli ortalama. Ilk dolu indeks: pencere-1.
 *
 * TOHUM SECIMI: ilk `pencere` degerin basit ortalamasi. Alternatif olan
 * "ilk fiyattan basla" tohumu daha erken deger uretir ama ilk barlarda
 * gercege uzak kalir ve TA-Lib ile uyusmaz. TA-Lib'in classic davranisi
 * secildi; olculdu, birebir tutuyor (bkz. testteki REF_EMA5/REF_EMA20).
 */
export function ema(degerler: number[], pencere: number): (number | null)[] {
  return emaTohumlu(degerler, pencere, pencere - 1)
}

/**
 * Bollinger bantlari. Orta bant = SMA(pencere), sapma = POPULASYON standart
 * sapmasi (N'e bolunur, N-1'e degil) - TA-Lib BBANDS ile ayni tanim.
 * Ust/alt = orta +/- katsayi * sapma.
 *
 * Sapma iki gecisli hesaplanir (once ortalama, sonra kare farklar): tek
 * gecisli sum/sumSq formulu buyuk fiyatlarda anlamli basamak kaybettirir.
 */
export function bollinger(
  degerler: number[],
  pencere: number,
  katsayi: number,
): { orta: (number | null)[]; ust: (number | null)[]; alt: (number | null)[] } {
  const orta = sma(degerler, pencere)
  const ust = bosSeri(degerler.length)
  const alt = bosSeri(degerler.length)
  for (let i = 0; i < degerler.length; i++) {
    const ortalama = orta[i]
    if (ortalama === null) continue
    let kareToplam = 0
    for (let j = i - pencere + 1; j <= i; j++) {
      const fark = degerler[j] - ortalama
      kareToplam += fark * fark
    }
    const sapma = Math.sqrt(kareToplam / pencere)
    ust[i] = ortalama + katsayi * sapma
    alt[i] = ortalama - katsayi * sapma
  }
  return { orta, ust, alt }
}

/**
 * RSI - WILDER yumusatmasi. Ilk dolu indeks: `pencere` (pencere-1 degil,
 * cunku `pencere` adet FARK icin pencere+1 adet fiyat gerekir).
 *
 * SECILEN TANIM (iki adim):
 *  1) Tohum: ilk `pencere` farkin BASIT ortalamasi -> ortKazanc, ortKayip.
 *  2) Sonrasi Wilder yumusatmasi: ort = (onceki*(pencere-1) + guncel)/pencere.
 *     (Bu, alfa = 1/pencere olan ustel ortalamadir; EMA'nin 2/(n+1)'i DEGIL.)
 *
 * RSI = 100 * ortKazanc / (ortKazanc + ortKayip). Bu bicim, RS = kazanc/kayip
 * uzerinden yazilan 100 - 100/(1+RS) ile cebirsel olarak ayni sonucu verir
 * ama kayip 0 iken sifira bolme yapmaz: dogrudan 100 cikar. Her ikisi de 0
 * ise (tamamen duz seri) hareket yoktur; TA-Lib gibi 0 dondurulur - bu deger
 * olculerek dogrulandi, varsayilmadi.
 */
export function rsi(degerler: number[], pencere: number): (number | null)[] {
  const sonuc = bosSeri(degerler.length)
  if (!tumuSonlu(degerler)) return sonuc
  if (pencere < 1 || pencere + 1 > degerler.length) return sonuc
  let ortKazanc = 0
  let ortKayip = 0
  for (let i = 1; i <= pencere; i++) {
    const fark = degerler[i] - degerler[i - 1]
    if (fark > 0) ortKazanc += fark
    else ortKayip -= fark
  }
  ortKazanc /= pencere
  ortKayip /= pencere
  sonuc[pencere] = rsiDegeri(ortKazanc, ortKayip)
  for (let i = pencere + 1; i < degerler.length; i++) {
    const fark = degerler[i] - degerler[i - 1]
    const kazanc = fark > 0 ? fark : 0
    const kayip = fark < 0 ? -fark : 0
    ortKazanc = (ortKazanc * (pencere - 1) + kazanc) / pencere
    ortKayip = (ortKayip * (pencere - 1) + kayip) / pencere
    sonuc[i] = rsiDegeri(ortKazanc, ortKayip)
  }
  return sonuc
}

/** Hareketsiz seride (kazanc+kayip=0) 0 doner; sifira bolme olusmaz. */
function rsiDegeri(ortKazanc: number, ortKayip: number): number {
  const toplam = ortKazanc + ortKayip
  if (toplam === 0) return 0
  return (100 * ortKazanc) / toplam
}

/**
 * MACD. macd = EMA(hizli) - EMA(yavas), sinyal = EMA(macd, sinyal),
 * histogram = macd - sinyal.
 *
 * ORTAK TOHUM NOKTASI (kritik ve sezgiye aykiri):
 * Iki EMA da kendi dogal baslangicinda DEGIL, ikisinin de hazir oldugu ORTAK
 * indekste tohumlanir: baslangic = max(hizli, yavas) - 1. Yani 12/26 icin
 * hizli EMA 11. barda degil, 25. barda (14..25 arasi 12 barlik SMA ile)
 * tohumlanir. Bu TA-Lib'in davranisidir ve birebir uyusmasi olculdu (fark 0).
 *
 * NEDEN bu secim: hizli EMA'yi kendi dogal indeksinde tohumlayan "naif"
 * yontem ayni veriyle FARKLI sayilar uretir - olculen sapma 33. indekste
 * 0.864, 40'ta 0.268, 50'de 0.051, 59'da 0.011 (sonuyor ama hicbir zaman
 * sifirlanmiyor). Iki tanim da savunulabilir; dogrulanabilir referansi olan
 * tanim secildi, cunku boylece cikti bagimsiz bir kaynakla sinanabiliyor.
 *
 * ISINMA FARKI (bilinerek birakildi): TA-Lib uc ciktiyi da tek bir lookback
 * ile kirpar, macd cizgisini de ancak (yavas-1)+(sinyal-1) = 33. indeksten
 * verir. Burada macd cizgisi hesaplanabildigi ilk indeksten (yavas-1 = 25)
 * itibaren doldurulur; bu degerler ayni ozyinelemeden gelir, uydurma degildir,
 * yalnizca TA-Lib'in API kirpmasi uygulanmaz. sinyal ve histogram ise dogal
 * olarak 33'ten baslar. Test bu yuzden referansi 33. indeksten itibaren
 * karsilastirir, 25..32 araligini ayri bir testle belgeler.
 */
export function macd(
  degerler: number[],
  hizli: number,
  yavas: number,
  sinyal: number,
): { macd: (number | null)[]; sinyal: (number | null)[]; histogram: (number | null)[] } {
  const n = degerler.length
  const macdSerisi = bosSeri(n)
  const sinyalSerisi = bosSeri(n)
  const histogram = bosSeri(n)
  if (hizli < 1 || yavas < 1 || sinyal < 1) {
    return { macd: macdSerisi, sinyal: sinyalSerisi, histogram }
  }
  const ortakBaslangic = Math.max(hizli, yavas) - 1
  const hizliEma = emaTohumlu(degerler, hizli, ortakBaslangic)
  const yavasEma = emaTohumlu(degerler, yavas, ortakBaslangic)

  const macdDolu: number[] = []
  for (let i = ortakBaslangic; i < n; i++) {
    const h = hizliEma[i]
    const y = yavasEma[i]
    if (h === null || y === null) continue
    const deger = h - y
    macdSerisi[i] = deger
    macdDolu.push(deger)
  }

  // Sinyal, macd cizgisinin YALNIZCA dolu bolumu uzerinde hesaplanir; null'lar
  // diziye girse ozyineleme kirilirdi. Sonuc ortakBaslangic kadar otelenir.
  const sinyalDolu = emaTohumlu(macdDolu, sinyal, sinyal - 1)
  for (let j = 0; j < sinyalDolu.length; j++) {
    const s = sinyalDolu[j]
    if (s === null) continue
    const i = ortakBaslangic + j
    const m = macdSerisi[i]
    sinyalSerisi[i] = s
    if (m !== null) histogram[i] = m - s
  }
  return { macd: macdSerisi, sinyal: sinyalSerisi, histogram }
}
