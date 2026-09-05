/**
 * 390px duzen korumasi.
 *
 * BU TESTIN SINIRI ACIKCA BELIRTILIR: gercek tasmayi yalnizca bir tarayici
 * olcebilir ve bu depoda frontend icin tarayici test altyapisi YOK. Olcum
 * elle yapildi ve sayisaldir:
 *     duzeltme ONCESI : belge genisligi 450px / goruntu 390px -> 60px TASMA
 *     duzeltme SONRASI: 390px / 390px -> tasma YOK
 * (Playwright ile, izole bir onizleme konteynerinde olculdu.)
 *
 * Buradaki test o olcumu TEKRARLAMAZ; tasmayi gideren ozelliklerin sessizce
 * SILINMESINI engeller. Zayif ama gercek bir korumadir: birisi flexWrap'i
 * veya minWidth:0'i kaldirirsa test duser ve olcumun neden yapildigi
 * hatirlanir.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const kok = dirname(dirname(fileURLToPath(import.meta.url)))
const kaynak = readFileSync(join(kok, 'components', 'DashboardBilesenleri.tsx'), 'utf8')
const sayfa = readFileSync(join(kok, 'src', 'app', 'dashboard', 'page.tsx'), 'utf8')

function govde(ad) {
  const i = kaynak.indexOf(`export function ${ad}(`)
  assert.ok(i > -1, `${ad} bulunamadi`)
  const j = kaynak.indexOf('\nexport ', i + 1)
  return kaynak.slice(i, j === -1 ? undefined : j)
}

test('ust bar dar ekranda SARAR', () => {
  const g = govde('UstBar')
  assert.match(g, /flexWrap:\s*'wrap'/, 'flexWrap kaldirilmis: 390px\'te 60px tasma geri gelir')
})

test('ust barda e-posta KIRPILIR ve dugmeyi ezmez', () => {
  const g = govde('UstBar')
  assert.match(g, /textOverflow:\s*'ellipsis'/, 'uzun e-posta kirpilmali')
  assert.match(g, /minWidth:\s*0/, 'minWidth:0 olmadan kirpma calismaz')
  assert.match(g, /flexShrink:\s*0/, 'cikis dugmesi ezilmemeli')
})

test('arama formu sarar ve girdi minWidth 0 tasir', () => {
  const g = govde('AramaFormu')
  assert.match(g, /flexWrap:\s*'wrap'/)
  // flex ogelerinin varsayilan min-width degeri "auto"dur; yer tutucu metni
  // girdiye taban genislik dayatir ve dugmeyi disari iter.
  assert.match(g, /minWidth:\s*0/, 'minWidth:0 olmadan yer tutucu metni tasma yaratir')
})

test('arama formunun GORUNUMU degistirilmedi (altin dolgulu dugme)', () => {
  const g = govde('AramaFormu')
  assert.match(g, /background:\s*'#D4AF37'/, 'dugme altin dolgulu kalmali')
  assert.match(g, /color:\s*'#0f172a'/)
  assert.match(g, /padding:\s*14/, 'girdi dolgusu korunmali')
})

test('kok kapsayici dolgusu dar ekranda kuculur', () => {
  assert.match(sayfa, /padding:\s*'clamp\(12px, 4vw, 32px\)'/,
    'sabit 32px dolgu 390px ekranin %16sini yiyordu')
})

test('page.tsx yalnizca default disa aktarir (Next.js kisiti)', () => {
  const disaAktarimlar = [...sayfa.matchAll(/^export .*/gm)].map(m => m[0])
  assert.equal(disaAktarimlar.length, 1, `beklenmeyen disa aktarim: ${disaAktarimlar}`)
  assert.match(disaAktarimlar[0], /^export default function Dashboard/)
})
