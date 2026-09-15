'use client'
import { useEffect, useRef } from 'react'
import { createChart, ColorType, CandlestickSeries, IChartApi, ISeriesApi } from 'lightweight-charts'

const MARKET_DATA_URL = process.env.NEXT_PUBLIC_MARKET_DATA_URL || 'http://localhost:8160'

type Props = {
  ticker: string
  // Koyfin olay katmani (EventOverlayLayer) icin EKLENDI - opsiyonel,
  // verilmezse eski davranis birebir korunur. Mum verisi yuklendikten
  // SONRA cagrilir (marker'lar ancak candle'lar varken anlamlidir).
  onHazir?: (chart: IChartApi, series: ISeriesApi<'Candlestick'>) => void
}

export default function PriceChart({ ticker, onHazir }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return
    containerRef.current.innerHTML = ''

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 300,
      layout: { background: { type: ColorType.Solid, color: '#ffffff' }, textColor: '#333' },
      grid: { vertLines: { visible: false }, horzLines: { color: '#eee' } },
    })
    const candleSeries = chart.addSeries(CandlestickSeries)

    fetch(`${MARKET_DATA_URL}/price/${ticker}`)
      .then((res) => res.json())
      .then((result) => {
        if (!result.data) return
        const candleData = result.data.map((c: any) => ({
          time: c.date,
          open: parseFloat(c.open),
          high: parseFloat(c.high),
          low: parseFloat(c.low),
          close: parseFloat(c.close),
        }))
        candleSeries.setData(candleData)
        chart.timeScale().fitContent()
        onHazir?.(chart, candleSeries)
      })
      .catch((err) => console.error('PriceChart veri hatasi:', err))

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [ticker])

  return <div ref={containerRef} />
}
