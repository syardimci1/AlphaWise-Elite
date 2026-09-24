// Kategori: YASAL UYARI RENDER (AB-043) — skor sentezi servisinin gonderdigi
// feragatname ekrana ULASMAK ZORUNDA.
//
// NEDEN KAYNAK TARAMASI: bu depoda jsdom yok ve kurulmayacak, yani bileseni
// gercekten render edip DOM'da metin aramak mumkun degil. Alternatif, hicbir
// sey test etmemekti. Kaynak taramasi zayif bir kanittir ama SIFIR degildir:
// asagidaki assert'lerin her biri, render'i kaldiran bir degisiklikte kirilir.
// Sinirini acikca yaziyorum: bu test "alan ekranda GORUNUYOR" demez,
// "kod alani render etmeye CALISIYOR ve sabit kopya kullanmiyor" der.
//
// NEDEN ONEMLI: alan 76. satirda TIP olarak taniniyordu ama govdede hic
// kullanilmiyordu. Tip tanimi bir soz degildir; derleyici "bu alan gelebilir"
// der, "bu alan gosterilir" demez. Fark tam olarak bu kusurdu.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const KOK = dirname(fileURLToPath(import.meta.url))
const KAYNAK = readFileSync(join(KOK, '..', 'components', 'PentagonSkor.tsx'), 'utf8')

/** Yorum satirlarini atar: bir garantinin YORUMDA gecmesi kanit degildir. */
const KOD = KAYNAK
  .replace(/\{\/\*[\s\S]*?\*\/\}/g, '')
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .split('\n')
  .filter((satir) => !satir.trim().startsWith('//'))
  .join('\n')

test('AB-043: yasal_uyari yalnizca TIP olarak degil, GOVDEDE de kullanilir', () => {
  const tipTanimi = /yasal_uyari\?:\s*string/.test(KOD)
  assert.ok(tipTanimi, 'tip tanimi kayboldu — sozlesme degistiyse test guncellenmeli')

  // Tip tanimi disindaki kullanimlari say. Tek kullanim = yalnizca tip = KUSUR.
  const tumKullanimlar = (KOD.match(/yasal_uyari/g) || []).length
  assert.ok(
    tumKullanimlar >= 3,
    `yasal_uyari ${tumKullanimlar} kez geciyor; tip + kosul + render icin en az 3 beklenir`,
  )
})

test('AB-043: render KOSULLUDUR — alan yoksa bos kutu cizilmez', () => {
  // Kosulsuz render, alan gelmediginde bos bir feragat kutusu birakirdi;
  // bu, verilmemis bir uyariyi verilmis gibi gostermek olurdu.
  assert.match(
    KOD,
    /\{veri\.yasal_uyari\s*&&/,
    'kosullu render (veri.yasal_uyari && ...) bulunamadi',
  )
})

test('AB-043: metin SERVISTEN gelir — on yuzde sabit feragat kopyasi YOK', () => {
  // Ayni metni iki yerde tutmak, ikisinin sessizce ayrismasi demektir.
  // Servisin gonderdigi metnin ayirt edici parcalari on yuz kaynaginda
  // HIC gecmemeli.
  for (const parca of [
    'yatirim danismanligi degildir',
    'yatırım danışmanlığı değildir',
    'YASAL UYARI:',
    'Gecmis performans',
    'Geçmiş performans',
  ]) {
    assert.ok(
      !KAYNAK.includes(parca),
      `on yuzde sabit feragat kopyasi bulundu: "${parca}"`,
    )
  }
})

test('AB-043: render besgen CIZIMINDEN SONRA gelir (geometri etkilenmez)', () => {
  // Blok <svg> agacinin ICINE konulsaydi besgen duzenini bozabilirdi.
  const svgSonu = KOD.lastIndexOf('</svg>')
  const uyariKonumu = KOD.search(/\{veri\.yasal_uyari\s*&&/)
  assert.ok(svgSonu !== -1, 'svg bulunamadi')
  assert.ok(uyariKonumu !== -1, 'yasal_uyari render bulunamadi')
  assert.ok(
    uyariKonumu > svgSonu,
    'yasal_uyari blogu svg agacinin ICINDE — besgen geometrisini etkileyebilir',
  )
})
