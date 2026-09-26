'use client'
// ============================================================================
// KARŞILAŞTIRMA GRAFİĞİ — 2-3 sembolün yüzde-normalize çizgileri + lejant
// ============================================================================
//
// Sözleşme: contracts/grafik/karsilastirma_modu.md · ADR-6.
// BİLEREK İNCE: hizalama, normalize, boşluk gösterimi ve lejant metinleri
// `@/lib/grafik/karsilastirma` saf modülünde karar verilir ve orada sınanır.
// Burada yalnızca kütüphane kurulumu, imleç aboneliği ve yaşam döngüsü var.
// Görünen sabit metin YOK (Y8 kapısı saf modüldeki tabloyu tarar).
import { useEffect, useMemo, useRef, useState } from 'react'
import { ColorType, LineSeries, LineStyle, createChart } from 'lightweight-charts'
import type { IChartApi, ISeriesApi, MouseEventParams, Time } from 'lightweight-charts'
import type { HizalamaSonucu } from '@/lib/grafik/karsilastirma'
import {
  KARSILASTIRMA_METINLERI,
  SERI_RENKLERI,
  cizgiVerisi,
  lejantSatirlari,
  tabanNotu,
  yuzdeMetni,
} from '@/lib/grafik/karsilastirma'

type Props = {
  sonuc: Extract<HizalamaSonucu, { durum: 'tamam' }>
  yukseklik: number
  renk: { metin: string; ikincil: string; soluk: string; cizgi: string; zemin: string }
}

/** Y10 ölçümü: veri → boyanmış kare süresi `performance` girdisi olarak kaydedilir (görünmez). */
export const CIZIM_OLCUMU = 'karsilastirma-cizim'

export default function KarsilastirmaGrafigi({ sonuc, yukseklik, renk }: Props) {
  const kutuRef = useRef<HTMLDivElement | null>(null)
  const grafikRef = useRef<IChartApi | null>(null)
  const [grafikHazir, setGrafikHazir] = useState(false)
  const [imlecTarihi, setImlecTarihi] = useState<string | null>(null)

  // 1) Grafik bir kez kurulur; seriler veri değişince yeniden kurulur (aşağıda).
  useEffect(() => {
    const kutu = kutuRef.current
    if (kutu === null) return
    const grafik = createChart(kutu, {
      width: kutu.clientWidth,
      height: yukseklik,
      layout: { background: { type: ColorType.Solid, color: renk.zemin }, textColor: renk.metin },
      grid: { vertLines: { color: renk.cizgi }, horzLines: { color: renk.cizgi } },
    })
    grafikRef.current = grafik
    setGrafikHazir(true)

    const imlec = (param: MouseEventParams<Time>): void => {
      setImlecTarihi(typeof param.time === 'string' ? param.time : null)
    }
    grafik.subscribeCrosshairMove(imlec)
    const boyutlandir = (): void => {
      if (kutuRef.current !== null) grafik.applyOptions({ width: kutuRef.current.clientWidth })
    }
    window.addEventListener('resize', boyutlandir)
    return () => {
      window.removeEventListener('resize', boyutlandir)
      grafik.unsubscribeCrosshairMove(imlec)
      setGrafikHazir(false)
      grafik.remove()
      grafikRef.current = null
    }
    // Bağımlılık KASTEN boş: renk/yükseklik modül sabitlerinden gelir; grafiği
    // yeniden kurmak kullanıcının yakınlaştırmasını sıfırlardı.
  }, [])

  // 2) Seriler. Taban çizgisi (%0) ilk seriye kesikli fiyat çizgisi olarak eklenir.
  useEffect(() => {
    if (!grafikHazir) return
    const grafik = grafikRef.current
    if (grafik === null) return
    performance.mark(`${CIZIM_OLCUMU}:baslangic`)
    const seriler: ISeriesApi<'Line', Time>[] = sonuc.seriler.map((seri, i) => {
      const cizgi = grafik.addSeries(LineSeries, {
        color: SERI_RENKLERI[seri.yuva],
        lineWidth: 2,
        // C3: fiyat eksenindeki son değer etiketi sembol adını taşır — kimlik yalnız renge bağlı değil.
        title: seri.sembol,
        priceLineVisible: false,
        lastValueVisible: true,
        // Eksen tabanın kendisi değil yüzde: kütüphanenin yüzde MODU kullanılmaz (taban kayar, ADR-6).
        priceFormat: { type: 'custom', formatter: yuzdeMetni, minMove: 0.01 },
      })
      // cizgiVerisi, kütüphanenin LineData | WhitespaceData şekliyle yapısal olarak aynıdır.
      cizgi.setData(cizgiVerisi(sonuc.eksen, seri.degerler))
      if (i === 0) {
        cizgi.createPriceLine({
          price: 0,
          color: renk.soluk,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: false,
          title: '',
        })
      }
      return cizgi
    })
    grafik.timeScale().fitContent()
    const kare = requestAnimationFrame(() => {
      performance.measure(CIZIM_OLCUMU, `${CIZIM_OLCUMU}:baslangic`)
    })
    return () => {
      cancelAnimationFrame(kare)
      // H-6: bileşen kaldırılırken React temizlikleri bildirim sırasıyla çalışır;
      // (1)'in temizliği grafiği ZATEN yok etmiştir ve yok edilmiş grafikte
      // removeSeries fırlatıp tüm terminal ağacını çökertir (gerçek Chromium'da
      // ölçüldü). Seriler yalnızca grafik hâlâ canlıysa tek tek sökülür.
      if (grafikRef.current !== grafik) return
      for (const cizgi of seriler) grafik.removeSeries(cizgi)
    }
  }, [grafikHazir, sonuc, renk.soluk])

  const satirlar = useMemo(() => lejantSatirlari(sonuc, imlecTarihi), [sonuc, imlecTarihi])

  return (
    <div>
      <div style={{ color: renk.ikincil, fontSize: 11, marginTop: 8 }}>{tabanNotu(sonuc.tabanTarihi)}</div>
      {/* C3: lejant grafiğin ÜSTÜNDE ve her zaman görünür; üzerine gelmeye bağlı değil. */}
      <ul
        aria-label={KARSILASTIRMA_METINLERI.lejant}
        style={{ listStyle: 'none', padding: 0, margin: '8px 0 0', display: 'grid', gap: 6 }}
      >
        {satirlar.map((satir) => (
          <li key={satir.sembol} style={{ fontSize: 12, color: renk.metin, overflowWrap: 'anywhere' }}>
            <span
              aria-hidden="true"
              style={{
                display: 'inline-block',
                width: 14,
                height: 3,
                borderRadius: 2,
                background: satir.renk,
                verticalAlign: 'middle',
                marginRight: 6,
              }}
            />
            <strong>{satir.sembol}</strong>
            {satir.anaMi && <span style={{ color: renk.soluk }}> ({KARSILASTIRMA_METINLERI.anaSembol})</span>}{' '}
            <span data-lejant-deger={satir.sembol}>{satir.degerMetni}</span>{' '}
            <span style={{ color: renk.soluk }}>{satir.tarih}</span>
            {satir.notlar.length > 0 && (
              <div data-lejant-not={satir.sembol} style={{ color: renk.ikincil, fontSize: 11, marginLeft: 20 }}>
                {satir.notlar.join(' · ')}
              </div>
            )}
          </li>
        ))}
      </ul>
      <div ref={kutuRef} data-karsilastirma-grafigi="" style={{ marginTop: 10 }} />
    </div>
  )
}
