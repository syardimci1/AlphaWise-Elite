/**
 * Mercek anahtarlarinin ARAYUZ ile SERVIS arasinda ayrismasini kilitler.
 *
 * Arayuzdeki liste, servisin src/mercek.py dosyasindaki anahtarlarla ayni
 * olmak zorunda. Ayrisirsa kullanici bir dugmeye basar, servis "bilinmeyen
 * mercek" der ve sessizce tarafsiz gorunum doner — dugme calisiyormus gibi
 * gorunur ama hicbir sey degismez.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const kok = dirname(dirname(fileURLToPath(import.meta.url)))
const depoKok = dirname(kok)

function servisAnahtarlari() {
  const yol = join(depoKok, 'skor-sentezi-service', 'src', 'mercek.py')
  const kaynak = readFileSync(yol, 'utf8')
  return [...kaynak.matchAll(/^\s*"anahtar":\s*(?:TARAFSIZ|"([a-z_]+)")/gm)]
    .map((m) => m[1] || 'tarafsiz')
}

function arayuzAnahtarlari() {
  const kaynak = readFileSync(join(kok, 'src', 'app', 'dashboard', 'page.tsx'), 'utf8')
  const blok = kaynak.match(/const MERCEKLER = \[([\s\S]*?)\n\]/)
  assert.ok(blok, 'arayuzde MERCEKLER listesi bulunamadi')
  return [...blok[1].matchAll(/anahtar:\s*'([a-z_]+)'/g)].map((m) => m[1])
}

test('arayuz ve servis mercek anahtarlari AYNI', () => {
  const servis = servisAnahtarlari()
  const arayuz = arayuzAnahtarlari()
  assert.ok(servis.length >= 4, `servis anahtarlari okunamadi: ${servis}`)
  assert.deepEqual([...arayuz].sort(), [...servis].sort(),
    `ayrisma: arayuz=${arayuz} servis=${servis}`)
})

test('tarafsiz mercek HER IKI tarafta da var', () => {
  assert.ok(servisAnahtarlari().includes('tarafsiz'))
  assert.ok(arayuzAnahtarlari().includes('tarafsiz'))
})

test('kontrol GERCEKTEN calisiyor (ayiklama dogru)', () => {
  const s = servisAnahtarlari()
  assert.ok(s.includes('temettu_odakli') && s.includes('risk_odakli'),
    `beklenen anahtarlar bulunamadi: ${s}`)
})
