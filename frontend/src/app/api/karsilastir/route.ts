import { NextRequest, NextResponse } from 'next/server'
import { tickerDogrula } from '@/lib/servis-proxy'
import { tabloGetir, AZAMI_SEMBOL } from '@/lib/karsilastirma-veri.js'

/**
 * Cok sembollu karsilastirma (Madde 29) — FAN-OUT SUNUCUDA.
 *
 * NEDEN TARAYICI DEGIL DE SUNUCU FAN-OUT YAPIYOR
 * ==============================================
 * OLCULDU: tek sembollu dashboard acilisi ZATEN 11 es zamanli /api istegi
 * harciyor ve middleware'deki 'sinyal' sinifinin anlik patlama tavani 35
 * (src/middleware.ts). Tarayici N sembol x M servis cagirsaydi 4 sembolde
 * bile ekran KENDI KENDINI 429'a dusururdu. Burada tarayici TEK istek yapar
 * (yani hiz sinirindan TEK jeton harcar), servisler arasi dagitim sunucuda
 * yapilir.
 *
 * HANGI SERVISLER — VE NEDEN BUNLAR
 * =================================
 * Yalnizca OLCULEREK hizli ve KOTASIZ oldugu dogrulanan uclar kullanilir
 * (sureler 08.09.2026'da MSFT ve daha once hic sorulmamis AMD ile olculdu):
 *     qlib /predict        0,019-0,030 s   yerel gunluk skor onbellegi
 *     market-data /price   0,053-0,075 s   merkezi CSV deposu
 *     taa /analyze         0,097-0,138 s   yerel hesap
 *     finra /darkpool      0,668 s         ucretsiz kamu verisi (FINRA)
 *     gamma /dix-like      0,075-0,881 s   FINRA verisinden turetilir
 *
 * BILEREK DISLANANLAR (olculen gerekcelerle):
 *     insider /ozet            soguk 10,2 s — tabloyu bekletir
 *     skor-sentezi /skor       onbelleksiz 20-40 s (kendi compose notunda yazili)
 *     institution-filter/*     sembol basina 1 LLMQuant kredisi, BAKIYE = 0
 *     gamma /gex               gunluk toplam 25 istek kotasi
 *     maa /decide              sembol basina ucretli fan-out (FMP+Tiingo+Finnhub)
 * Bu dislama BUTCE KURALININ geregidir: cok sembollu bir ekran, kotali bir
 * ucu cagirdiginda maliyeti sembol sayisiyla CARPAR.
 *
 * HER HUCRE OLCULEMEDI OLABILIR
 * =============================
 * Bir servis yanit vermezse o hucre null doner ve NEDENI tasinir; sifir
 * YAZILMAZ. Sifir ile "olculemedi" ayrimi bu depoda 232d1a0 ile kurulmustur.
 */

export async function GET(req: NextRequest) {
  const ham = req.nextUrl.searchParams.get('semboller') || ''
  const istenen = ham.split(/[\s,;]+/).map((s) => s.trim()).filter(Boolean)

  const gecerli: string[] = []
  const reddedilen: string[] = []
  for (const s of istenen) {
    const t = tickerDogrula(s)
    if (!t) { if (!reddedilen.includes(s)) reddedilen.push(s); continue }
    if (!gecerli.includes(t)) gecerli.push(t)
  }
  const kesilen = gecerli.slice(AZAMI_SEMBOL)
  const semboller = gecerli.slice(0, AZAMI_SEMBOL)

  if (semboller.length === 0) {
    return NextResponse.json(
      { hata: 'Geçerli sembol verilmedi', reddedilen, azami: AZAMI_SEMBOL },
      { status: 400 })
  }

  // Fan-out mantigi src/lib/karsilastirma-veri.js icinde ve TESTLIDIR
  // (8 birim testi). Burada tutulsaydi, /api/* oturum istedigi icin hicbir
  // yerde tek basina kosulamazdi.
  const satirlar = await tabloGetir(semboller)

  return NextResponse.json({
    semboller, reddedilen, kesilen, azami: AZAMI_SEMBOL,
    satirlar,
    kaynaklar: [
      { ad: 'Qlib günlük skor', uc: '/predict', not: 'yerel önbellek, kota yok' },
      { ad: 'Teknik analiz', uc: '/analyze', not: 'yerel hesap, kota yok' },
      { ad: 'DPKE', uc: '/dix-like', not: 'FINRA verisinden türetilir; resmî DIX değildir' },
      { ad: 'Dark pool hacmi', uc: '/darkpool', not: 'FINRA ATS, ücretsiz kamu verisi' },
    ],
    dislanan_kaynaklar: [
      'İçeriden işlem özeti (soğuk ölçüm 10,2 sn)',
      'Beş eksenli skor (önbelleksiz 20-40 sn)',
      'Kurum filtresi (sembol başına 1 LLMQuant kredisi; bakiye 0)',
      'Gamma GEX (günlük 25 istek kotası)',
      'MAA kararı (sembol başına ücretli fan-out)',
    ],
    not: ('Boş hücre "ölçülemedi" demektir, sıfır değil. Bu ekran karar kodu '
          + 'ÜRETMEZ; yalnızca ölçülebilen değerleri yan yana koyar.'),
  })
}
