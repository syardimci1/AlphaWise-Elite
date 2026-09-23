// Grafik katmani - Zaman Dilimi (resample) modulu.
//
// Gunluk barlari ISO haftasi / takvim ayi kovalarina indirger. SAF modul:
// DOM yok, Date.now() yok, rastgelelik yok -> ayni girdi hep ayni cikti.
//
// ZAMAN KARARI (DST tuzagi): tarih ayristirmasi icin koyfin-zaman.ts'deki
// Date.UTC tabanli yardimcilar kullanilir. O dosya depo genelinde "tarih
// ayristirmasi YALNIZCA burada yapilir" kuralini ilan ettigi icin ayni mantigi
// yeniden yazmak yerine ona bagimli oluyoruz.
// new Date('2026-06-16') UTC, new Date(2026, 5, 16) ise YEREL yorumlanir;
// ikisini de kullanmiyoruz. Neden: yerel saat diliminde UTC gece yarisi bir
// onceki/sonraki gune dusebilir (or. America/New_York'ta 2026-03-09 UTC gece
// yarisi yerelde 2026-03-08 Pazar'dir) ve bar bir onceki ISO haftasina
// yazilirdi. Bu yuzden okuma da yalnizca getUTC* ile yapilir ve gun aritmetigi
// UTC ms uzerinde yurutulur - UTC'de DST olmadigi icin bir gun HER ZAMAN tam
// 86400000 ms'dir (yerel saatte bu 23 veya 25 saat olabilirdi).
import { gunStringindenUtcMs, utcMsToIsGunuString } from '../koyfin-zaman'

export type Bar = {
  tarih: string // "YYYY-MM-DD"
  acilis: number
  yuksek: number
  dusuk: number
  kapanis: number
  hacim: number
}

export type ZamanDilimi = 'gunluk' | 'haftalik' | 'aylik'

/**
 * hamBarlariCevir sonucu.
 * NOT: gorev tanimindaki `: Bar[]` imzasi yerine bilincli olarak bu nesne
 * donuluyor. "Kac kayit atlandi" bilgisi cagirana ULASMAK ZORUNDA (Y3 /
 * sessiz yutma yasagi); ciplak bir dizi bu sayiyi gorunmez kilardi.
 */
export type CevirmeSonucu = {
  barlar: Bar[]
  atlanan: number
}

export type ResampleSonucu = {
  barlar: Bar[]
  turetildi: boolean
  eksikSonKova: boolean
  /**
   * Gecersiz tarihli oldugu icin ELENEN bar sayisi (S5, 23.09.2026).
   *
   * NEDEN RAPORLANIYOR: onceden gecersiz tarihli bir Bar sessizce geciyordu ve
   * kova anahtari NaN uzerinden uretiliyordu. Sessizce elemek de ayni derecede
   * kotu olurdu - cagiran taraf "23 bar verdim, 22 aldim" farkini goremezdi.
   * `hamBarlariCevir`'in `atlanan` alaniyla ayni desen.
   */
  atlanan: number
}

const GUN_MS = 86_400_000

/**
 * "YYYY-MM-DD" -> UTC ms; bicim ya da takvim olarak gecersizse null.
 * Dogrulama gidis-donus ile yapilir: Date.UTC tasma yapan degerleri sessizce
 * duzeltir ('2026-02-30' -> 2026-03-02, '2026-13-01' -> 2027-01-01, '0026-..'
 * -> 1926), geri cevirince girdiden farkli cikarlar ve reddedilirler. Tek bir
 * karsilastirma hem bicimi hem takvim gecerliligini kapsar.
 */
function gecerliGunMs(gun: string): number | null {
  const ms = gunStringindenUtcMs(gun)
  if (!Number.isFinite(ms)) return null
  return utcMsToIsGunuString(ms) === gun ? ms : null
}

/**
 * Ham alani sayiya cevirir; cevrilemiyorsa null.
 * Servis sayilari STRING gonderdigi icin string kabul edilir, ama once TIP
 * suzulur: Number('') / Number(null) / Number([]) hepsi 0 doner ve bos bir alan
 * "0 fiyat" olarak sisteme sizardi (Y3: uydurma veri yok).
 */
function sayiyaCevir(deger: unknown): number | null {
  if (typeof deger === 'number') return Number.isFinite(deger) ? deger : null
  if (typeof deger !== 'string') return null
  const kirpilmis = deger.trim()
  if (kirpilmis === '') return null
  const sayi = Number(kirpilmis)
  return Number.isFinite(sayi) ? sayi : null
}

/** Tek bir ham kaydi Bar'a cevirir; herhangi bir alan bozuksa null (= atlanir). */
function tekKayidiCevir(kayit: unknown): Bar | null {
  if (typeof kayit !== 'object' || kayit === null) return null
  const alanlar = kayit as Record<string, unknown>

  const tarih = alanlar.date
  if (typeof tarih !== 'string' || gecerliGunMs(tarih) === null) return null

  const acilis = sayiyaCevir(alanlar.open)
  const yuksek = sayiyaCevir(alanlar.high)
  const dusuk = sayiyaCevir(alanlar.low)
  const kapanis = sayiyaCevir(alanlar.close)
  const hacim = sayiyaCevir(alanlar.volume)
  // Kismi bar YOK: eksik alani tamamlamak uydurmak olurdu, kayit butunuyle atlanir.
  if (acilis === null || yuksek === null || dusuk === null || kapanis === null || hacim === null) {
    return null
  }
  return { tarih, acilis, yuksek, dusuk, kapanis, hacim }
}

/** /price yanit zarfindan ({ data: [...] }) ya da ciplak diziden kayit listesi cikarir. */
function kayitListesiCikar(ham: unknown): unknown[] | null {
  if (Array.isArray(ham)) return ham
  if (typeof ham === 'object' && ham !== null) {
    const veri = (ham as { data?: unknown }).data
    if (Array.isArray(veri)) return veri
  }
  return null
}

/**
 * market-data-service /price/{ticker} yanitini Bar[]'a cevirir.
 * Bozuk/eksik kayitlari ATLAR ve kac tane atladigini `atlanan` ile birlikte
 * dondurur - cagiran taraf "veri eksik" uyarisini gosterebilsin diye.
 */
export function hamBarlariCevir(ham: unknown): CevirmeSonucu {
  const kayitlar = kayitListesiCikar(ham)
  // Zarfin kendisi tanimsizsa ATLANACAK KAYIT da yoktur; atlanan=0 dogru sayidir
  // (bos sonuc + 0 atlanan = "hic veri gelmedi", 0'dan buyuk atlanan = "veri bozuk").
  if (kayitlar === null) return { barlar: [], atlanan: 0 }

  const barlar: Bar[] = []
  let atlanan = 0
  for (const kayit of kayitlar) {
    const bar = tekKayidiCevir(kayit)
    if (bar === null) atlanan += 1
    else barlar.push(bar)
  }
  return { barlar, atlanan }
}

/** getUTCDay() 0=Pazar doner; ISO'da Pazar 7'dir. NaN girdi NaN dondurur (cokmez). */
function isoGunNumarasi(ms: number): number {
  const gun = new Date(ms).getUTCDay()
  return gun === 0 ? 7 : gun
}

/** Kova anahtari: barin ait oldugu ISO haftasinin PAZARTESI gunu ("YYYY-MM-DD"). */
function isoHaftaAnahtari(tarih: string): string {
  const ms = gunStringindenUtcMs(tarih)
  return utcMsToIsGunuString(ms - (isoGunNumarasi(ms) - 1) * GUN_MS)
}

/** Kova anahtari: takvim ayi ("YYYY-MM"). Tarih bicimi dogrulanmis oldugu icin
 * dilimlemek yeterli - gereksiz Date donusumu yapilmaz. */
function ayAnahtari(tarih: string): string {
  return tarih.slice(0, 7)
}

/** Ayni ISO haftasinin Pazar gunu (periyot sonu). */
function haftaSonuMs(ms: number): number {
  return ms + (7 - isoGunNumarasi(ms)) * GUN_MS
}

/** Icinde bulunulan takvim ayinin son gunu. Date.UTC(yil, ay+1, 0) = bir sonraki
 * ayin "0. gunu" = bu ayin son gunu; artik yil tablosu tutmaya gerek kalmaz. */
function aySonuMs(ms: number): number {
  const d = new Date(ms)
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)
}

/**
 * Son kova tamamlandi mi? Modul SAF oldugu icin "bugun"u bilemez; karar yalnizca
 * VERIDEN verilir: son barin tarihinden sonra, ayni periyot icinde hala bir hafta
 * ici gun (Pzt-Cum) kaliyorsa kova acik sayilir. Ornek: hafta Cuma ile bitiyorsa
 * kapali, Carsamba ile bitiyorsa acik; ay 31'inde bitiyorsa kapali, 10'unda aciktir.
 *
 * SINIR: resmi tatil takvimi bilinmedigi icin periyot sonuna dusen bir tatil
 * (or. 25 Aralik Cuma) kovayi gereksiz yere "eksik" gosterebilir. Hata yonu
 * bilincli olarak guvenli tarafa egilmistir: yarim bir kovayi "tam" diye
 * gostermektense tam bir kovayi "eksik" diye gostermek tercih edilir.
 */
function sonKovaEksikMi(sonBarTarihi: string, dilim: 'haftalik' | 'aylik'): boolean {
  const sonMs = gunStringindenUtcMs(sonBarTarihi)
  if (!Number.isFinite(sonMs)) return false
  const periyotSonuMs = dilim === 'haftalik' ? haftaSonuMs(sonMs) : aySonuMs(sonMs)
  for (let ms = sonMs + GUN_MS; ms <= periyotSonuMs; ms += GUN_MS) {
    const isoGun = isoGunNumarasi(ms)
    if (isoGun <= 5) return true // Pzt-Cum: potansiyel islem gunu hala var
  }
  return false
}

/**
 * Bir kovadaki barlari tek bara indirger.
 * acilis=ilk, yuksek=maks, dusuk=min, kapanis=son, hacim=TOPLAM.
 */
function kovayiBirlestir(grup: Bar[]): Bar {
  const ilk = grup[0]
  const son = grup[grup.length - 1]
  let yuksek = ilk.yuksek
  let dusuk = ilk.dusuk
  let hacim = 0
  for (const bar of grup) {
    if (bar.yuksek > yuksek) yuksek = bar.yuksek
    if (bar.dusuk < dusuk) dusuk = bar.dusuk
    hacim += bar.hacim
  }
  return {
    // Kova etiketi: kovadaki ILK GERCEK barin tarihi. Periyodun Pazartesi'sini /
    // ayin 1'ini yazmiyoruz; o gun tatil ya da hafta sonuysa veride KARSILIGI
    // OLMAYAN bir tarih uretmis olurduk (Y3: var olmayan veri uydurulmaz).
    tarih: ilk.tarih,
    acilis: ilk.acilis,
    yuksek,
    dusuk,
    kapanis: son.kapanis,
    hacim,
  }
}

/**
 * Gunluk barlari istenen zaman dilimine indirger.
 * EKSIK GUN ENTERPOLE EDILMEZ: yalnizca var olan barlar toplanir, hafta sonu ve
 * tatil bosluklari oldugu gibi birakilir (kova icindeki bar sayisi degisken olabilir).
 */
export function resample(barlar: Bar[], dilim: ZamanDilimi): ResampleSonucu {
  // S5 (23.09.2026): gecersiz tarihli barlar HER YOLDA elenir. Onceden yalnizca
  // `hamBarlariCevir`'den gecen veri korunuyordu; dogrudan Bar[] veren bir
  // cagiran icin savunma yoktu ve bozuk tarih NaN kova anahtari uretiyordu.
  // Eleme gunluk yolda da yapilir: aksi halde ayni bozuk bar gunlukte gecer,
  // haftalikta duserdi - S4'te sikayet edilen yollar-arasi tutarsizligin aynisi.
  const temiz = barlar.filter((b) => gecerliGunMs(b.tarih) !== null)
  const atlanan = barlar.length - temiz.length

  if (dilim === 'gunluk') {
    // "Aynen doner": icerik degismez.
    //
    // S4 (23.09.2026): burada `barlar.slice()` vardi ve yorum "saflik
    // garantisi" diyordu, ama slice YALNIZCA diziyi kopyalar - eleman
    // nesneleri paylasilir kalir, `sonuc.barlar[0].kapanis = 999` girdiyi de
    // bozardi. Haftalik/aylik yol zaten YENI nesne uretiyordu, yani iddia
    // yanlis olmakla kalmiyor, iki yol arasinda tutarsizlik da yaratiyordu.
    return {
      barlar: temiz.map((b) => ({ ...b })),
      turetildi: false,
      eksikSonKova: false,
      atlanan,
    }
  }
  if (temiz.length === 0) {
    return { barlar: [], turetildi: true, eksikSonKova: false, atlanan }
  }

  // "Ilk/son" semantigi tarih sirasina bagli; girdinin sirali geldigine GUVENMIYORUZ.
  // "YYYY-MM-DD" bicimi sozluksel sirada kronolojiktir, bu yuzden Date donusumu
  // gerekmez. sort kararli oldugu icin ayni tarihli barlar girdi sirasini korur.
  const sirali = temiz.slice().sort((a, b) => (a.tarih < b.tarih ? -1 : a.tarih > b.tarih ? 1 : 0))

  const kovalar = new Map<string, Bar[]>()
  for (const bar of sirali) {
    const anahtar = dilim === 'haftalik' ? isoHaftaAnahtari(bar.tarih) : ayAnahtari(bar.tarih)
    const mevcut = kovalar.get(anahtar)
    if (mevcut === undefined) kovalar.set(anahtar, [bar])
    else mevcut.push(bar)
  }

  // Map ekleme sirasini korur, girdi de tarihe gore sirali; kovalar kronolojik cikar.
  const cikti: Bar[] = []
  for (const grup of kovalar.values()) cikti.push(kovayiBirlestir(grup))

  const sonBar = sirali[sirali.length - 1]
  return {
    barlar: cikti,
    turetildi: true,
    eksikSonKova: sonKovaEksikMi(sonBar.tarih, dilim),
    atlanan,
  }
}
