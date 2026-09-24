// Kalicilik yazimlarinin debounce'u - contracts/grafik/kalicilik_sozlesmesi.md C5.
//
// NEDEN ANAHTAR BASINA: gosterge ve cizim, ve farkli semboller AYRI anahtarlara
// yazilir. Tek bir ortak zamanlayici, AAPL'nin bekleyen yazimini TSLA'ya
// gecildiginde iptal eder ve AAPL'deki son degisikligi sessizce kaybederdi.
//
// NEDEN YAZIM KAPANIS OLARAK GELIR: planlandigi andaki anahtar ve veri
// kapanista yakalanir. Yazim 300 ms sonra ya da bosaltmada calistiginda o an
// hangi sembol/kullanici acik olursa olsun, veri AIT OLDUGU anahtara gider.
//
// Zamanlayici disaridan verilir: testler gercek zaman beklemeden,
// deterministik bir saatle kosar.

/**
 * Olculen yazim maliyeti (gercek Chromium, kanit/kalicilik/e2e P1): 1000 cizimde
 * p95 4.8 ms. Yani gecikme tek yazimin maliyeti icin DEGIL, art arda gelen
 * yazim patlamalari (hizli gosterge ac/kapa, geri al/yinele serisi) icindir.
 * 300 ms: bir insanin ardisik tiklamalari arasindaki tipik araligi kapsar;
 * kayip penceresi ise pagehide/gizlenme/kaldirmada bosaltmayla kapatilir.
 */
export const KAYIT_GECIKMESI_MS = 300

export interface Zamanlayici {
  kur(is: () => void, ms: number): unknown
  iptal(tutamac: unknown): void
}

const tarayiciZamanlayicisi: Zamanlayici = {
  kur: (is, ms) => setTimeout(is, ms),
  iptal: (tutamac) => clearTimeout(tutamac as ReturnType<typeof setTimeout>),
}

export class GecikmeliKayit {
  private readonly bekleyenler = new Map<string, { tutamac: unknown; yaz: () => void }>()

  constructor(
    private readonly ms: number = KAYIT_GECIKMESI_MS,
    private readonly zamanlayici: Zamanlayici = tarayiciZamanlayicisi,
  ) {}

  /** Anahtarin bekleyen yazimini bununla DEGISTIRIR ve pencereyi yeniden baslatir. */
  planla(anahtar: string, yaz: () => void): void {
    this.iptal(anahtar)
    const tutamac = this.zamanlayici.kur(() => {
      this.bekleyenler.delete(anahtar)
      yaz()
    }, this.ms)
    this.bekleyenler.set(anahtar, { tutamac, yaz })
  }

  /** Anahtarin bekleyen yazimini yapmadan duser (sifirlama: silinen kayit geri yazilmasin). */
  iptal(anahtar: string): void {
    const bekleyen = this.bekleyenler.get(anahtar)
    if (bekleyen === undefined) return
    this.zamanlayici.iptal(bekleyen.tutamac)
    this.bekleyenler.delete(anahtar)
  }

  /**
   * Bekleyen tum yazimlari HEMEN yapar (sekme kapanisi, bilesen kaldirma).
   * Biri firlatsa bile digerleri yapilir; ilk hata sonra yeniden firlatilir -
   * yutulmaz.
   */
  bosalt(): void {
    const isler = [...this.bekleyenler.values()]
    for (const { tutamac } of isler) this.zamanlayici.iptal(tutamac)
    this.bekleyenler.clear()
    let ilkHata: unknown = null
    for (const { yaz } of isler) {
      try {
        yaz()
      } catch (hata) {
        if (ilkHata === null) ilkHata = hata
      }
    }
    if (ilkHata !== null) throw ilkHata
  }

  bekleyenSayisi(): number {
    return this.bekleyenler.size
  }
}
