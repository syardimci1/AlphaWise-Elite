/**
 * Bildirim merkezinin KARAR mantigi — saf ve test edilebilir.
 *
 * NEDEN AYRI MODUL
 * ================
 * Buradaki tek kural, sistemdeki en tehlikeli sessiz hatayi engeller:
 * "alarm yok" ile "bakamadim" ayni gorunemez. Bu kurali bir React
 * bileseninin icine gomsek, testi olmayan bir yerde yasardi.
 */

export const DUZEY_RENK = {
  kritik: '#f87171',
  alarm: '#fb923c',
  uyari: '#fbbf24',
  bilgi: '#94a3b8',
}

export function duzeyRengi(duzey) {
  return DUZEY_RENK[duzey] || DUZEY_RENK.bilgi
}

/**
 * Ust satirda gosterilecek durum.
 * Doner: { metin, renk, vurgulu }
 */
export function durumOzeti(ozet) {
  if (!ozet) {
    return { metin: 'Bildirim servisi yanıt vermedi', renk: DUZEY_RENK.alarm,
             vurgulu: true }
  }
  const okunamayan = ozet.okunamayan_kaynak || 0
  const toplam = ozet.toplam_olay || 0
  if (toplam === 0 && okunamayan === 0) {
    return { metin: 'Açık alarm yok', renk: '#4ade80', vurgulu: false }
  }
  if (toplam === 0 && okunamayan > 0) {
    // EN KRITIK DAL: liste bos ama kaynak okunamadi. "Alarm yok" YAZILAMAZ.
    return {
      metin: `${okunamayan} kaynak okunamadı — liste boş olması "alarm yok" demek DEĞİLDİR`,
      renk: DUZEY_RENK.alarm, vurgulu: true,
    }
  }
  const k = (ozet.duzey_sayimi && ozet.duzey_sayimi.kritik) || 0
  const parcalar = [`${toplam} açık kayıt`]
  if (k > 0) parcalar.push(`${k} kritik`)
  if (okunamayan > 0) parcalar.push(`${okunamayan} kaynak okunamadı`)
  return {
    metin: parcalar.join(' · '),
    renk: k > 0 ? DUZEY_RENK.kritik : DUZEY_RENK.alarm,
    vurgulu: k > 0 || okunamayan > 0,
  }
}

/** Rozet sayisi: kritik + alarm (uyari/bilgi rozete girmez). */
export function rozetSayisi(ozet) {
  if (!ozet || !ozet.duzey_sayimi) return 0
  return (ozet.duzey_sayimi.kritik || 0) + (ozet.duzey_sayimi.alarm || 0)
}

/** Kaynak durumu icin kisa etiket. */
export function kaynakEtiketi(durum) {
  if (durum === 'okundu') return { metin: 'okundu', renk: '#4ade80' }
  if (durum === 'kaynak_yok') return { metin: 'kaynak yok', renk: '#94a3b8' }
  return { metin: 'OKUNAMADI', renk: DUZEY_RENK.alarm }
}
