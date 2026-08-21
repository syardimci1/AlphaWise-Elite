import { NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'

// Raporlar dizinindeki PDF'leri listeler. Dizin konteynere SALT OKUNUR
// baglanir; bu route hicbir kosulda yazma yapmaz.
const RAPOR_DIZINI = process.env.REPORTS_DIR || '/reports'

// Yalnizca bu desene uyan dosya adlari kabul edilir. Yol ayiraci (/ veya \),
// nokta-nokta (..) ve gizli dosyalar bu desenle zaten disarida kalir.
const GUVENLI_AD = /^[A-Za-z0-9][A-Za-z0-9_-]*\.pdf$/

function tarihAyikla(ad: string): string | null {
  const m = ad.match(/(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : null
}

export async function GET() {
  try {
    // withFileTypes: yalnizca DOSYALARI al, alt dizinlere (orn. araclar/) girme
    const girdiler = await fs.readdir(RAPOR_DIZINI, { withFileTypes: true })

    const raporlar = await Promise.all(
      girdiler
        .filter((g) => g.isFile() && GUVENLI_AD.test(g.name))
        .map(async (g) => {
          const bilgi = await fs.stat(path.join(RAPOR_DIZINI, g.name))
          return {
            dosya: g.name,
            tarih: tarihAyikla(g.name),
            boyut: bilgi.size,
            degistirilme: bilgi.mtime.toISOString(),
            tur: g.name.startsWith('gunsonu_raporu') ? 'Gün Sonu Raporu'
               : g.name.startsWith('gunsonu_prompt_paketi') ? 'Prompt Paketi'
               : g.name.startsWith('alphawise_kullanim_kilavuzu') ? 'Kullanım Kılavuzu'
               : 'Belge',
          }
        })
    )

    // En yeni en ustte (tarih yoksa dosya adina gore)
    raporlar.sort((a, b) => (b.tarih || b.dosya).localeCompare(a.tarih || a.dosya))

    return NextResponse.json({ raporlar })
  } catch (err: any) {
    if (err?.code === 'ENOENT') {
      return NextResponse.json({ raporlar: [], not: 'Rapor dizini bulunamadi' })
    }
    return NextResponse.json({ error: 'Raporlar listelenemedi: ' + err.message }, { status: 500 })
  }
}
