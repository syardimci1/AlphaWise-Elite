// VERI PENCERESI — /price proxy'sine gecirilen `limit` parametresinin dogrulanmasi.
//
// NEDEN VAR (FAZ 1'de olculen R4 riski):
// market-data-service'in /price/{ticker} ucu `limit` parametresi kabul ediyor
// (varsayilan 60). Ama frontend proxy'si bu parametreyi ILETMIYORDU. Sonuc:
// grafik her zaman ~60 bar (~3 ay) gosteriyordu, oysa olay katmanindaki
// kaynaklar (13F ceyreklik, kongre islemleri ~1 yil) cok daha geriye gidiyor.
// Bu pencerenin disina dusen marker'lar icin mum YOK — yani olaylar SESSIZCE
// kayboluyordu. Cok zaman dilimli gorunum (haftalik/aylik turetme) de yeterli
// gecmis olmadan anlamsiz kalirdi.
//
// NEDEN AYRI, SAF BIR MODUL:
// Dogrulama mantigi rota fonksiyonunun icinde kalsaydi yalnizca bir HTTP
// istegi kurarak test edilebilirdi. Burada saf oldugu icin sinir degerleri
// (0, negatif, ondalik, tasma, bos dize) DOM'suz ve agsiz test edilir.

/** Kabul edilen en kucuk pencere. 0 ve negatif anlamsiz, ustelik yukari akista tanimsiz. */
export const LIMIT_ALT = 1

/**
 * Kabul edilen en buyuk pencere.
 *
 * OLCUM: yukari akis 2020-01-02 -> 2026-09-10 arasi 1681 bar donduruyor ve
 * limit=10000 verilse bile 1681'de tavanlaniyor. Yani 2000 pratikte "tum
 * gecmis" demek; ustu bir sey istemek yukari akista fazladan is yaratmaz ama
 * istemcinin sinirsiz bir pencere istemesini de engeller.
 */
export const LIMIT_UST = 2000

export type LimitSonuc =
  | { durum: 'yok' }
  | { durum: 'gecerli'; limit: number }
  | { durum: 'gecersiz'; sebep: string }

/**
 * Sorgu dizesinden gelen ham `limit` degerini dogrular.
 *
 * TASARIM KARARI — gecersiz deger SESSIZCE YOK SAYILMAZ:
 * `limit=abc` gonderen bir istemciye 60 barlik varsayilan donseydi, istemci
 * "1500 bar istedim, 60 geldi" durumunu fark edemezdi; grafik eksik veriyle
 * dogru gorunurdu. Bu yuzden gecersiz deger cagirana 400 ile bildirilir
 * (fail-loud). Parametrenin HIC verilmemesi ise gecerli bir durumdur ve eski
 * cagiranlarin davranisini birebir korur (geriye uyumluluk).
 */
export function limitDogrula(ham: string | null | undefined): LimitSonuc {
  if (ham === null || ham === undefined || ham === '') return { durum: 'yok' }

  // Number() bos/bosluklu dizeyi 0'a cevirir ve '1e3', '0x10', '12.5' gibi
  // bicimleri de kabul eder. Bunlar "bar sayisi" olarak anlamsiz oldugu icin
  // once bicimi sabitliyoruz: yalnizca ondalik basamaklar.
  if (!/^\d+$/.test(ham)) {
    return { durum: 'gecersiz', sebep: 'limit yalnizca rakamlardan olusmalidir' }
  }

  const sayi = Number(ham)
  if (!Number.isSafeInteger(sayi)) {
    return { durum: 'gecersiz', sebep: 'limit cok buyuk' }
  }
  if (sayi < LIMIT_ALT) {
    return { durum: 'gecersiz', sebep: `limit en az ${LIMIT_ALT} olmalidir` }
  }
  if (sayi > LIMIT_UST) {
    return { durum: 'gecersiz', sebep: `limit en fazla ${LIMIT_UST} olabilir` }
  }
  return { durum: 'gecerli', limit: sayi }
}

/**
 * Dogrulanmis sonucu yukari akis yoluna eklenecek sorgu dizesine cevirir.
 * 'yok' durumunda BOS dize doner — yani yukari akisin kendi varsayilani calisir.
 */
export function limitSorguDizesi(sonuc: LimitSonuc): string {
  return sonuc.durum === 'gecerli' ? `?limit=${sonuc.limit}` : ''
}
