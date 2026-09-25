// Kategori: KARŞILAŞTIRMA S2 (C1, C4, Y9) — ortak taban, yüzde normalize, dürüst hizalama.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hizalaVeNormalizeEt, type GirdiSerisi } from '../../src/lib/grafik/karsilastirma'

function seri(sembol: string, yuva: 0 | 1 | 2, ciftler: [string, number][]): GirdiSerisi {
  return { sembol, yuva, barlar: ciftler.map(([tarih, kapanis]) => ({ tarih, kapanis })) }
}

const yakin = (gercek: number | null, beklenen: number): void => {
  assert.notEqual(gercek, null)
  assert.ok(Math.abs((gercek as number) - beklenen) < 1e-9, `${gercek} ≈ ${beklenen} değil`)
}

test('C1: taban gününde HER seri tam %0, sonraki günler tabana göre yüzde değişim', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('AAA', 0, [['2026-01-02', 100], ['2026-01-05', 110], ['2026-01-06', 90]]),
    seri('BBB', 1, [['2026-01-02', 50], ['2026-01-05', 55], ['2026-01-06', 75]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  assert.equal(sonuc.tabanTarihi, '2026-01-02')
  assert.deepEqual(sonuc.eksen, ['2026-01-02', '2026-01-05', '2026-01-06'])
  const [a, b] = sonuc.seriler
  assert.equal(a.degerler[0], 0)
  assert.equal(b.degerler[0], 0)
  yakin(a.degerler[1], 10)
  yakin(a.degerler[2], -10)
  yakin(b.degerler[1], 10)
  yakin(b.degerler[2], 50)
})

test('C1 / FAZ4: çok farklı fiyat ölçeği (1 000 kat) normalize sonrası AYNI yüzde yolunu verir', () => {
  // Normalize olmadan: 5 $'lık hisse ile 5 000 $'lık hisse aynı eksende çizilince
  // ucuz olanın ±%20'si ekranın dibinde düz bir çizgidir. Normalize sonrası
  // aynı göreli hareket birebir aynı değerlerdir.
  const sonuc = hizalaVeNormalizeEt([
    seri('UCUZ', 0, [['2026-02-02', 5], ['2026-02-03', 6], ['2026-02-04', 4]]),
    seri('PAHALI', 1, [['2026-02-02', 5000], ['2026-02-03', 6000], ['2026-02-04', 4000]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  assert.deepEqual(sonuc.seriler[0].degerler, sonuc.seriler[1].degerler)
  yakin(sonuc.seriler[0].degerler[1], 20)
  yakin(sonuc.seriler[1].degerler[2], -20)
})

test('C1: farklı başlangıç → taban EN GEÇ başlayanın ilk ortak günü; öncesi dışarıda ve sayılır', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('ESKI', 0, [['2026-01-02', 10], ['2026-01-05', 20], ['2026-01-06', 40], ['2026-01-07', 44]]),
    seri('YENI', 1, [['2026-01-06', 100], ['2026-01-07', 90]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  // "Aynı nokta, farklı gün" olmasın: ESKI'nin %0'ı 2026-01-02'deki 10 değil, 06'daki 40'tır.
  assert.equal(sonuc.tabanTarihi, '2026-01-06')
  assert.deepEqual(sonuc.eksen, ['2026-01-06', '2026-01-07'])
  assert.equal(sonuc.seriler[0].tabanKapanis, 40)
  assert.equal(sonuc.seriler[0].tabanOncesi, 2)
  assert.equal(sonuc.seriler[1].tabanOncesi, 0)
  yakin(sonuc.seriler[0].degerler[1], 10)
  yakin(sonuc.seriler[1].degerler[1], -10)
})

test('C1: taban günü, geç başlayanın ilk günü diğerinde EKSİKSE bir sonraki ORTAK güne kayar', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-03-02', 10], ['2026-03-04', 11], ['2026-03-05', 12]]),
    seri('B', 1, [['2026-03-03', 20], ['2026-03-04', 22], ['2026-03-05', 24]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  // B 03'te başlıyor ama A'da 03 yok: 03 taban OLAMAZ (A için %0 uydurulurdu).
  assert.equal(sonuc.tabanTarihi, '2026-03-04')
  assert.equal(sonuc.seriler[0].degerler[0], 0)
  assert.equal(sonuc.seriler[1].degerler[0], 0)
})

test('Y9 / C4: bir seride eksik gün NULL kalır — enterpolasyon yok, son değer taşınmaz', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-04-01', 100], ['2026-04-02', 102], ['2026-04-03', 104], ['2026-04-06', 108]]),
    seri('B', 1, [['2026-04-01', 50], ['2026-04-03', 60], ['2026-04-06', 70]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  assert.deepEqual(sonuc.eksen, ['2026-04-01', '2026-04-02', '2026-04-03', '2026-04-06'])
  const b = sonuc.seriler[1]
  assert.equal(b.degerler.length, sonuc.eksen.length, 'her seri eksenle bire bir hizalı olmalı')
  assert.equal(b.degerler[1], null, 'eksik gün: enterpolasyon (%10) ya da LOCF (%0) DEĞİL, null')
  assert.deepEqual(b.eksikTarihler, ['2026-04-02'])
  assert.deepEqual(sonuc.seriler[0].eksikTarihler, [])
})

test('FAZ4: HİÇBİR seride barı olmayan gün eksende yer almaz (uydurulmaz, eksik sayılmaz)', () => {
  // 2026-04-08 iki seride de yok: takvim verisi olmadan "orada bar olmalıydı" denemez.
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-04-07', 10], ['2026-04-09', 11]]),
    seri('B', 1, [['2026-04-07', 20], ['2026-04-09', 22]]),
    seri('C', 2, [['2026-04-07', 30], ['2026-04-09', 33]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  assert.deepEqual(sonuc.eksen, ['2026-04-07', '2026-04-09'])
  for (const s of sonuc.seriler) {
    assert.deepEqual(s.eksikTarihler, [])
    assert.ok(s.degerler.every((d) => d !== null))
  }
})

test('C4: serinin son barından SONRAKİ günler boşluk sayılmaz; sonTarih raporlanır', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-05-01', 10], ['2026-05-04', 11], ['2026-05-05', 12]]),
    seri('B', 1, [['2026-05-01', 20], ['2026-05-04', 21]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  const b = sonuc.seriler[1]
  assert.equal(b.degerler[2], null)
  assert.deepEqual(b.eksikTarihler, [])
  assert.equal(b.sonTarih, '2026-05-04')
  assert.equal(sonuc.seriler[0].sonTarih, '2026-05-05')
})

test('Y3: geçersiz kapanış (0, negatif, NaN) değer üretmez; sayılır ve o gün veri yok olur', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-06-01', 10], ['2026-06-02', 11], ['2026-06-03', 12], ['2026-06-04', 13], ['2026-06-05', 14]]),
    seri('B', 1, [['2026-06-01', 10], ['2026-06-02', 0], ['2026-06-03', -5], ['2026-06-04', Number.NaN], ['2026-06-05', 15]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  const b = sonuc.seriler[1]
  assert.equal(b.gecersizKapanis, 3)
  assert.deepEqual(b.degerler.slice(1, 4), [null, null, null])
  assert.deepEqual(b.eksikTarihler, ['2026-06-02', '2026-06-03', '2026-06-04'])
  yakin(b.degerler[4], 50)
})

test('Y3: sırasız girdi sıralanır; yinelenen tarih ilk gelenle tutulur ve geçersiz sayılır', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-07-03', 12], ['2026-07-01', 10], ['2026-07-02', 11]]),
    seri('B', 1, [['2026-07-01', 5], ['2026-07-02', 6], ['2026-07-02', 999], ['2026-07-03', 7]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  assert.deepEqual(sonuc.eksen, ['2026-07-01', '2026-07-02', '2026-07-03'])
  yakin(sonuc.seriler[0].degerler[2], 20)
  yakin(sonuc.seriler[1].degerler[1], 20)
  assert.equal(sonuc.seriler[1].gecersizKapanis, 1)
})

test('FAZ4: tek seri (ya da verisi olan tek seri) → karşılaştırma YOK, durum "yetersiz"', () => {
  assert.equal(hizalaVeNormalizeEt([seri('A', 0, [['2026-01-02', 1]])]).durum, 'yetersiz')
  const bosla = hizalaVeNormalizeEt([seri('A', 0, [['2026-01-02', 1]]), seri('B', 1, [])])
  assert.equal(bosla.durum, 'yetersiz')
  if (bosla.durum === 'yetersiz') assert.deepEqual(bosla.verisiz, ['B'])
})

test('C1: tarih aralıkları hiç kesişmiyorsa durum "ortak-gun-yok" (sahte taban yok)', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-01-02', 1], ['2026-01-05', 2]]),
    seri('B', 1, [['2026-02-02', 1], ['2026-02-03', 2]]),
  ])
  assert.equal(sonuc.durum, 'ortak-gun-yok')
})

test('C1: bölünme benzeri tek günlük >%40 hareket İŞARETLENİR (düzeltme iddia edilmez)', () => {
  const sonuc = hizalaVeNormalizeEt([
    seri('A', 0, [['2026-08-03', 100], ['2026-08-04', 50], ['2026-08-05', 51], ['2026-08-06', 70]]),
    seri('B', 1, [['2026-08-03', 10], ['2026-08-04', 10.5], ['2026-08-05', 11], ['2026-08-06', 11]]),
  ])
  assert.equal(sonuc.durum, 'tamam')
  if (sonuc.durum !== 'tamam') return
  // -%50 işaretlenir; 51 -> 70 (+%37,3) eşiğin altında kalır.
  assert.deepEqual(sonuc.seriler[0].buyukSicramaTarihleri, ['2026-08-04'])
  assert.deepEqual(sonuc.seriler[1].buyukSicramaTarihleri, [])
})

test('Y10: 3 sembol × 2 yıl (504 gün) hizalama + normalize ≤ 50 ms (saf kısım)', () => {
  const girdiler: GirdiSerisi[] = [0, 1, 2].map((y) => {
    const barlar = []
    for (let i = 0; i < 504; i += 1) {
      const gun = new Date(Date.UTC(2024, 0, 2) + i * 86_400_000).toISOString().slice(0, 10)
      if (y === 2 && i % 50 === 7) continue // gerçekçi boşluklar
      barlar.push({ tarih: gun, kapanis: 100 + y * 10 + Math.sin(i / 9) * 5 })
    }
    return { sembol: `S${y}`, yuva: y as 0 | 1 | 2, barlar }
  })
  hizalaVeNormalizeEt(girdiler) // ısınma
  const bas = performance.now()
  const sonuc = hizalaVeNormalizeEt(girdiler)
  const sure = performance.now() - bas
  assert.equal(sonuc.durum, 'tamam')
  assert.ok(sure <= 50, `süre ${sure.toFixed(2)} ms`)
})
