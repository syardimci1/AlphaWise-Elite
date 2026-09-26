// Kayitli ayarlari sifirlama (C6) ve sekmeler arasi degisiklik algisi.
// contracts/grafik/kalicilik_sozlesmesi.md
import { anahtarUret, sil, type Depo, type KaydetSonucu } from './cizim-kalicilik'
import { gostergeAnahtari, gostergeleriSil } from './gosterge-kalicilik'
import type { GecikmeliKayit } from './gecikmeli-kayit'
import { karsilastirmaAnahtari, karsilastirmaSil } from './karsilastirma-kalicilik'

/**
 * Kullanicinin BU sembol icin kayitli gosterge, cizim ve karsilastirma
 * secimini siler (karsilastirma: contracts/grafik/karsilastirma_modu.md C5).
 *
 * SIRA ONEMLI: once bekleyen (debounce'lu) yazimlar iptal edilir. Tersi
 * yapilsaydi silinen kayit en fazla 300 ms sonra bekleyen yazimla geri
 * gelirdi - kullanici "sifirladim" sanarken ayarlari yenilemede donerdi.
 */
export function kayitlariSifirla(
  depo: Depo,
  kayitci: GecikmeliKayit,
  kullaniciKimligi: string,
  sembol: string,
): KaydetSonucu {
  kayitci.iptal(anahtarUret(kullaniciKimligi, sembol))
  kayitci.iptal(gostergeAnahtari(kullaniciKimligi, sembol))
  kayitci.iptal(karsilastirmaAnahtari(kullaniciKimligi, sembol))
  const hatalar = [
    sil(depo, kullaniciKimligi, sembol),
    gostergeleriSil(depo, kullaniciKimligi, sembol),
    karsilastirmaSil(depo, kullaniciKimligi, sembol),
  ]
    .filter((sonuc) => !sonuc.basarili)
    .map((sonuc) => sonuc.hata ?? '')
  return hatalar.length === 0 ? { basarili: true } : { basarili: false, hata: hatalar.join('; ') }
}

/**
 * Baska bir sekmenin `storage` olayi bu ad alanini ilgilendiriyor mu?
 * `key === null`, baska sekmede `localStorage.clear()` demektir: izlenen
 * kayitlar da gitmistir, bu da bir degisikliktir.
 */
export function baskaSekmeDegistirdi(olayAnahtari: string | null, izlenenler: readonly string[]): boolean {
  return olayAnahtari === null || izlenenler.includes(olayAnahtari)
}
