import { NextRequest } from 'next/server'
import { istekKimligi, servisProxy } from '@/lib/servis-proxy'
import { rolKapisi, izinliRoller, type Rol } from '@/lib/rol'

// Bildirim merkezi (Madde 28). Ticker almaz; sistem geneli alarm ozetidir.
//
// ----------------------------------------------------------------------------
// NEDEN ROL KAPISI VAR — OLCULDU (20.09.2026), VARSAYILMADI
// ----------------------------------------------------------------------------
// Canli /bildirimler yaniti su satirlari dondurdu:
//   * "[ana:claude1] ALARM: claude CALISMIYOR (pane_pid=3960990). Yeniden
//      baslatiliyor: 'claude --continue' (ardisik deneme: 1/6)"
//   * godmode_paper "MUTABAKAT ALARMI: Kontrol calistirilamadi ..."
//   * "ALARM: Haftalik egitim BASARISIZ veya HIC TETIKLENMEDI!"
// Yani besleme, sistemin ISLETIM MIMARISINI aciga veriyor: otomasyonun tmux
// pencerelerinde yeniden baslatilan Claude oturumlariyla yurudugu, surec
// kimlikleri ve ic saglik durumu. Sinif: KULLANICI-GIZLI degil, SISTEM-GIZLI
// — raporlar ucundaki ile AYNI sinif.
//
// Capraz-kullanici sizintisi DEGIL (icerik herkes icin ayni), bu yuzden
// kullanici bazli bolmek yanlis cozum olurdu; dogru cozum rol kapisidir.
//
// ⚠ DUZELTME (22.09.2026). Burada once "URUN ETKISI SIFIR: hicbir arayuz
// bileseni bu ucu cagirmiyor" yaziyordu. YANLISTI. O arama yalnizca
// frontend/src altinda yapilmisti; cagiran bilesen o agacin DISINDA:
//     frontend/components/BildirimMerkezi.tsx:28  fetch('/api/bildirimler')
// ve dashboard'da render ediliyor (src/app/dashboard/page.tsx:1079).
//
// GERCEK URUN ETKISI: role='user' bir hesapta bu widget veri yerine
// "Bu beslemeye erisim yetkiniz yok" mesajini gosterir. Bilesen hatayi
// zarifce ele aliyor (BildirimMerkezi.tsx:30 -> d?.hata ? setHata(...))
// yani ekran COKMEZ, yalnizca bu kutu bilgi yerine yetki metni yazar.
//
// Kapi yine de DOGRU karardir: icerik sistem isletim kaydidir (tmux
// pencere adlari, surec kimlikleri, ic saglik durumu) ve bir musteriye
// gitmemelidir. Degisen sey karar degil, o kararin URUN MALIYETININ
// dogru raporlanmasidir - "sifir" degil, "yetkisiz rolde kutu bilgi
// yerine yetki mesaji gosterir".
//
// Varsayilan admin+partner: bugunku iki hesap erisimini aynen korur.
// BILDIRIM_IZINLI_ROLLER ile daraltilabilir (orn. yalnizca "admin").
const VARSAYILAN_ROLLER: Rol[] = ['admin', 'partner']

export async function GET(req: NextRequest) {
  // Kapi, asagi akis servisine DOKUNMADAN once: yetkisiz cagiran, yanit
  // suresinden beslemenin dolu mu bos mu oldugunu cikaramasin.
  const red = await rolKapisi(
    req,
    izinliRoller(process.env.BILDIRIM_IZINLI_ROLLER, VARSAYILAN_ROLLER),
    'Bu beslemeye erisim yetkiniz yok',
    'Bildirim merkezi sistem isletim kayitlaridir ve yalnizca yetkili rollere aciktir.',
  )
  if (red) return red

  return servisProxy({
    taban: process.env.BILDIRIM_URL || 'http://alphawise-bildirim:8000',
    yol: '/bildirimler?azami=40',
    zamanAsimiMs: 15_000,
    servisAdi: 'Bildirim merkezi',
    kimlik: istekKimligi(req),
  })
}
