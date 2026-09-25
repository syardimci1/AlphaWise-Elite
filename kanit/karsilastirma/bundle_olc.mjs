// /dashboard JS paketi ölçümü: app-build-manifest.json'daki /dashboard/page JS dosyalarının
// ham ve gzip-9 toplamı. Kullanım: (frontend içinde `npx next build` sonrası)
//   node ../kanit/karsilastirma/bundle_olc.mjs .
// Aynı yöntem kalıcılık işinde kullanıldı (kanit/kalicilik/faz0_taban.md).
import { readFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { join } from 'node:path'
const kok = process.argv[2]
const man = JSON.parse(readFileSync(join(kok, '.next/app-build-manifest.json'), 'utf8'))
const dosyalar = man.pages['/dashboard/page'].filter((f) => f.endsWith('.js'))
let ham = 0, gz = 0
for (const f of dosyalar) { const b = readFileSync(join(kok, '.next', f)); ham += b.length; gz += gzipSync(b, { level: 9 }).length }
console.log(JSON.stringify({ dosya: dosyalar.length, ham, gzip9: gz }))
