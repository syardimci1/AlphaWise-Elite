/**
 * Next.js App Router DISA AKTARIM kisitlarini kilitler.
 *
 * NEDEN BU TEST VAR
 * =================
 * Bu kisit iki kez PRODUKSIYON DERLEMESINI dusurdu ve iki kez de
 * `tsc --noEmit` onu YAKALAMADI — yalnizca gercek `next build` yakaladi:
 *
 *   1. page.tsx'ten bilesen disa aktarildi:
 *      "Property 'BolgeKarti' ... not assignable to type 'never'"
 *   2. route.ts'ten sabit disa aktarildi:
 *      "Route ... does not match the required types of a Next.js Route."
 *
 * Yani tip kontrolu tek basina yeterli bir kapi DEGIL. Bu test, o kapiyi
 * derlemeden ONCE ve saniyeler icinde kurar.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const kok = dirname(dirname(fileURLToPath(import.meta.url)))
const APP = join(kok, 'src', 'app')

// Next.js'in bir route dosyasinda kabul ettigi disa aktarimlar.
const ROUTE_IZINLI = new Set([
  'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS',
  'dynamic', 'dynamicParams', 'revalidate', 'fetchCache', 'runtime',
  'preferredRegion', 'maxDuration', 'generateStaticParams',
])
// Bir page dosyasinda yalnizca default + belirli yapilandirmalar.
const PAGE_IZINLI = new Set([
  'metadata', 'generateMetadata', 'viewport', 'generateViewport',
  'dynamic', 'dynamicParams', 'revalidate', 'fetchCache', 'runtime',
  'preferredRegion', 'maxDuration', 'generateStaticParams',
])

function dosyalariBul(dizin, ad) {
  const cikti = []
  for (const g of readdirSync(dizin)) {
    const y = join(dizin, g)
    if (statSync(y).isDirectory()) cikti.push(...dosyalariBul(y, ad))
    else if (g === ad) cikti.push(y)
  }
  return cikti
}

/** Kaynaktaki ADLANDIRILMIS disa aktarimlar (default haric). */
function adlandirilmisDisaAktarimlar(kaynak) {
  const adlar = []
  for (const m of kaynak.matchAll(/^export\s+(?:async\s+)?(?:function|const|let|var|class)\s+(\w+)/gm)) {
    adlar.push(m[1])
  }
  for (const m of kaynak.matchAll(/^export\s*\{([^}]*)\}/gm)) {
    for (const p of m[1].split(',')) {
      const ad = p.trim().split(/\s+as\s+/).pop().trim()
      if (ad) adlar.push(ad)
    }
  }
  for (const m of kaynak.matchAll(/^export\s+type\s+(\w+)/gm)) adlar.push(m[1])
  return adlar
}

test('route.ts dosyalari YALNIZCA izinli adlari disa aktarir', () => {
  const dosyalar = dosyalariBul(APP, 'route.ts')
  assert.ok(dosyalar.length > 10, `beklenenden az route bulundu: ${dosyalar.length}`)
  for (const d of dosyalar) {
    for (const ad of adlandirilmisDisaAktarimlar(readFileSync(d, 'utf8'))) {
      assert.ok(ROUTE_IZINLI.has(ad),
        `${d.replace(kok, '')}: "${ad}" gecerli bir Route disa aktarimi degil ` +
        `(next build bunu reddeder; tsc --noEmit YAKALAMAZ)`)
    }
  }
})

test('page.tsx dosyalari YALNIZCA izinli adlari disa aktarir', () => {
  const dosyalar = dosyalariBul(APP, 'page.tsx')
  assert.ok(dosyalar.length >= 2, `beklenenden az page bulundu: ${dosyalar.length}`)
  for (const d of dosyalar) {
    for (const ad of adlandirilmisDisaAktarimlar(readFileSync(d, 'utf8'))) {
      assert.ok(PAGE_IZINLI.has(ad),
        `${d.replace(kok, '')}: "${ad}" gecerli bir Page disa aktarimi degil`)
    }
  }
})

test('kontrol GERCEKTEN calisiyor (yanlis pozitif/negatif yok)', () => {
  assert.deepEqual(adlandirilmisDisaAktarimlar('export const AZAMI_SEMBOL = 8'), ['AZAMI_SEMBOL'])
  assert.deepEqual(adlandirilmisDisaAktarimlar('export { AZAMI_SEMBOL }'), ['AZAMI_SEMBOL'])
  assert.deepEqual(adlandirilmisDisaAktarimlar('export { a as b }'), ['b'])
  assert.deepEqual(adlandirilmisDisaAktarimlar('export async function GET() {}'), ['GET'])
  assert.deepEqual(adlandirilmisDisaAktarimlar('export default function X() {}'), [],
    'default disa aktarim adlandirilmis SAYILMAZ')
})
