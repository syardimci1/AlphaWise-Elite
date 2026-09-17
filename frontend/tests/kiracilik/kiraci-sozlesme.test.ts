// Kategori: KİRACI SÖZLEŞMESİ — başlık adları ve kimlik okuma.
//
// Bu testlerin varlık nedeni somut bir hatadır: 16.09.2026 denetiminde
// middleware 'x-kullanici-id' yazarken tüketici 'x-alphawise-kullanici'
// okuyordu. Her iki taraf da kendi testinden geçiyor, zincir sessizce
// kopuyordu. Aşağıdaki ilk test tam olarak bunu kilitler.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { NextRequest } from 'next/server'
import {
  KULLANICI_BASLIGI,
  KIRACI_BASLIGI,
  SISTEM_KIRACI,
  kimlikDogrula,
  basliklariTemizle,
  kimlikOku,
  anahtarBileseni,
} from '../../src/lib/kiraci'

const A = 'c59c7853-b752-44ca-b40d-c4eb09798b50' // selcuk@alphawise.test
const B = 'd7e28a7c-d217-4abd-8fa5-ddc93d869d60' // partner@alphawise.test

function istek(basliklar: Record<string, string> = {}): NextRequest {
  return new NextRequest('http://localhost/api/raporlar', { headers: basliklar })
}

// --------------------------------------------------------------- ad sözleşmesi
test('SÖZLEŞME: başlık adları TEK kaynakta ve mimari belgesiyle aynı', () => {
  // Bu değerler kanit/faz1_mimari.md'de belgelenen adlardır. Değişirlerse
  // middleware ile tüketici arasındaki zincir kopar — ve o kopuş sessizdir.
  assert.equal(KULLANICI_BASLIGI, 'x-kullanici-id')
  assert.equal(KIRACI_BASLIGI, 'x-kiraci-sinifi')
  assert.equal(SISTEM_KIRACI, 'sistem')
})

test('SÖZLEŞME: yazan ve okuyan AYNI sabiti kullanınca zincir kapanır', () => {
  // Uçtan uca minyatür: yazma tarafı sabiti kullanır, okuma tarafı da.
  const b = new Headers()
  b.set(KULLANICI_BASLIGI, A)
  b.set(KIRACI_BASLIGI, 'kullanici')
  const k = kimlikOku(b)
  assert.equal(k?.kullaniciId, A)
  assert.equal(k?.kiraci, 'kullanici')
})

// ------------------------------------------------------------- kimlikDogrula
test('KİMLİK: geçerli UUID kabul edilir ve küçük harfe indirilir', () => {
  assert.equal(kimlikDogrula(A), A)
  assert.equal(kimlikDogrula(A.toUpperCase()), A)
  assert.equal(kimlikDogrula(`  ${B}  `), B)
})

test('KİMLİK: sistem kiracısı kabul edilir', () => {
  assert.equal(kimlikDogrula('sistem'), 'sistem')
})

test('KİMLİK: bozuk/tehlikeli değerler REDDEDİLİR (sessizce düzeltilmez)', () => {
  for (const kotu of [
    '', '   ', null, undefined,
    '../../etc/passwd',
    'c59c7853-b752-44ca-b40d-c4eb09798b50/../x', // yol aşımı denemesi
    'DROP TABLE',
    'sistem2',
    'c59c7853b75244cab40dc4eb09798b50',           // tire yok
    'zzzzzzzz-b752-44ca-b40d-c4eb09798b50',       // hex değil
  ]) {
    assert.equal(kimlikDogrula(kotu as any), null, `kabul edilmemeliydi: ${kotu}`)
  }
})

// --------------------------------------------------- basliklariTemizle (taklit)
test('TAKLİT: gelen istekteki kiraci başlıkları KOŞULSUZ silinir', () => {
  // Saldırgan kendi kimliğini uydurmaya çalışıyor.
  const r = istek({
    [KULLANICI_BASLIGI]: B,
    [KIRACI_BASLIGI]: 'kullanici',
    'x-baska': 'korunmali',
  })
  const temiz = basliklariTemizle(r)
  assert.equal(temiz.get(KULLANICI_BASLIGI), null)
  assert.equal(temiz.get(KIRACI_BASLIGI), null)
  // Diğer başlıklar bozulmamalı — temizlik dar olmalı.
  assert.equal(temiz.get('x-baska'), 'korunmali')
})

test('TAKLİT: temizlik sonrası kimlik okunamaz (silme gerçekten etkili)', () => {
  const r = istek({ [KULLANICI_BASLIGI]: B, [KIRACI_BASLIGI]: 'kullanici' })
  assert.equal(kimlikOku(basliklariTemizle(r)), null)
})

// ------------------------------------------------------------------ kimlikOku
test('OKUMA: kimlik yoksa null döner — karar çağırana bırakılır', () => {
  assert.equal(kimlikOku(new Headers()), null)
})

test('OKUMA: geçersiz kimlik null döner, sistem kiracısına DÜŞMEZ', () => {
  const b = new Headers()
  b.set(KULLANICI_BASLIGI, 'uydurma-deger')
  b.set(KIRACI_BASLIGI, 'kullanici')
  assert.equal(kimlikOku(b), null)
})

test('OKUMA: tanınmayan kiracı sınıfı sisteme düşer (dar tarafta hata)', () => {
  for (const sinif of ['admin', 'KULLANICI', 'root', '']) {
    const b = new Headers()
    b.set(KULLANICI_BASLIGI, A)
    b.set(KIRACI_BASLIGI, sinif)
    assert.equal(kimlikOku(b)?.kiraci, 'sistem', `sinif=${sinif}`)
  }
})

test('OKUMA: kiracı sınıfı hiç yoksa sisteme düşer', () => {
  const b = new Headers()
  b.set(KULLANICI_BASLIGI, A)
  assert.equal(kimlikOku(b)?.kiraci, 'sistem')
})

test('TUTARLILIK: sistem kimliği "kullanici" sınıfı taşıyamaz', () => {
  const b = new Headers()
  b.set(KULLANICI_BASLIGI, SISTEM_KIRACI)
  b.set(KIRACI_BASLIGI, 'kullanici')
  const k = kimlikOku(b)
  assert.equal(k?.kullaniciId, SISTEM_KIRACI)
  assert.equal(k?.kiraci, 'sistem')
})

// ------------------------------------------------------------ anahtarBileseni
test('ANAHTAR: üretilen bileşen yol ayırıcı ya da .. İÇEREMEZ', () => {
  for (const id of [A, B, SISTEM_KIRACI]) {
    const p = anahtarBileseni({ kullaniciId: id, kiraci: 'kullanici' })
    assert.ok(!p.includes('/'), `bolu icermemeli: ${p}`)
    assert.ok(!p.includes('\\'), `ters bolu icermemeli: ${p}`)
    assert.ok(!p.includes('..'), `.. icermemeli: ${p}`)
    assert.ok(!p.includes(':'), `iki nokta icermemeli (redis anahtari): ${p}`)
  }
})

test('ANAHTAR: doğrulanmamış kimlik ile anahtar üretimi HATA fırlatır', () => {
  assert.throws(
    () => anahtarBileseni({ kullaniciId: '../gizli', kiraci: 'kullanici' }),
    /dogrulanmamis kimlik/,
  )
})

test('ANAHTAR: iki farklı kullanıcı FARKLI bileşen üretir', () => {
  const a = anahtarBileseni({ kullaniciId: A, kiraci: 'kullanici' })
  const b = anahtarBileseni({ kullaniciId: B, kiraci: 'kullanici' })
  assert.notEqual(a, b)
})
