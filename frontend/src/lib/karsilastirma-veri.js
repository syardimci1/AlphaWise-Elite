/**
 * Cok sembollu karsilastirmanin VERI TOPLAMA mantigi (Madde 29).
 *
 * NEDEN ROUTE'UN ICINDE DEGIL
 * ===========================
 * /api/* uclari middleware geregi oturum ister; bu yuzden route'un kendisi
 * bir konteynerde tek basina sinanamiyor. Mantik burada saf tutulunca hem
 * sahte bir fetch ile birim testi yazilabiliyor hem de gercek servislere
 * karsi (host portlariyla) canli duman testi kosulabiliyor. Route ince bir
 * sarmalayici olarak kaliyor.
 *
 * HER HUCRE OLCULEMEDI OLABILIR
 * =============================
 * Bir servis yanit vermezse hucre null doner ve NEDENI tasinir. Sifir
 * YAZILMAZ: 0 gercek bir olcumdur.
 */

export const AZAMI_SEMBOL = 8

export function varsayilanTabanlar(icAglar = true) {
  return icAglar
    ? {
        qlib: 'http://alphawise-qlib:8000',
        taa: 'http://alphawise-taa:8000',
        gamma: 'http://alphawise-gamma-exposure:8000',
        finra: 'http://alphawise-finra-darkpool:8000',
      }
    : {
        qlib: 'http://127.0.0.1:8050',
        taa: 'http://127.0.0.1:8001',
        gamma: 'http://127.0.0.1:8220',
        finra: 'http://127.0.0.1:8200',
      }
}

async function guvenli(fetchImpl, url, sec, zamanAsimiMs) {
  try {
    const y = await fetchImpl(url, { signal: AbortSignal.timeout(zamanAsimiMs) })
    if (!y.ok) return { deger: null, hata: `HTTP ${y.status}` }
    return { deger: sec(await y.json()), hata: null }
  } catch (e) {
    const zamanAsimi = e?.name === 'TimeoutError' || e?.name === 'AbortError'
    return { deger: null, hata: zamanAsimi ? 'zaman aşımı' : (e?.message || 'ulaşılamadı') }
  }
}

export async function sembolSatiri(ticker, { fetchImpl = fetch, tabanlar,
                                             zamanAsimiMs = 8000 } = {}) {
  const T = tabanlar || varsayilanTabanlar(true)
  const e = encodeURIComponent(ticker)
  const [qlib, taa, dpke, finra] = await Promise.all([
    guvenli(fetchImpl, `${T.qlib}/predict/${e}`, (v) => {
      // OLCULDU (08.09.2026): kapsam disi bir sembolde qlib HTTP 200 doner ama
      // govdede {"error":"bu hisse icin skor yok ...","score":null} tasir.
      // ok=true'ya bakip gecersek kullanici BOS bir hucre gorur ve NEDENINI
      // hicbir yerde bulamaz.
      if (v?.error) throw new Error(v.error)
      return { skor: v?.score ?? null, tarih: v?.as_of_date ?? null }
    }, zamanAsimiMs),
    guvenli(fetchImpl, `${T.taa}/analyze/${e}`, (v) => {
      // Ayni desen: taa BRK.B icin HTTP 200 + {"error":"BRK.B icin veri bulunamadi"}.
      if (v?.error) throw new Error(v.error)
      return { kapanis: v?.last_close ?? null, rsi: v?.rsi_14 ?? null,
               sma20: v?.sma_20 ?? null, sma50: v?.sma_50 ?? null }
    }, zamanAsimiMs),
    guvenli(fetchImpl, `${T.gamma}/dix-like/${e}`, (v) => {
      if (v?.error) throw new Error(v.error)
      if (v?.veri_var === false) throw new Error('bu sembol için DPKE verisi yok')
      return { dpke: v?.cari_hafta?.dpke_yuzde ?? null,
               ortalama: v?.baglam?.ortalama_dpke_yuzde ?? null }
    }, zamanAsimiMs),
    guvenli(fetchImpl, `${T.finra}/darkpool/${e}`, (v) => {
      // EN TEHLIKELI DURUM (canli olcumde bulundu): var olmayan bir sembolde
      // FINRA ucu veri_var=false DONER ama ats_toplam_shares alanina 0 yazar.
      // Bu 0'i olculmus gibi gostermek, "olculemedi != sifir" ayrimini tam
      // olarak cignerdi — kullanici "bu hissede hic dark pool islemi yok"
      // sanardi.
      if (v?.error) throw new Error(v.error)
      if (v?.veri_var === false) throw new Error('bu sembol için FINRA verisi yok')
      return { atsHisse: v?.dark_pool?.ats_toplam_shares ?? null,
               hafta: v?.week_start_date ?? null }
    }, zamanAsimiMs),
  ])
  return {
    ticker,
    qlib_skoru: qlib.deger?.skor ?? null,
    qlib_tarih: qlib.deger?.tarih ?? null,
    son_kapanis: taa.deger?.kapanis ?? null,
    rsi_14: taa.deger?.rsi ?? null,
    sma_20: taa.deger?.sma20 ?? null,
    sma_50: taa.deger?.sma50 ?? null,
    dpke_yuzde: dpke.deger?.dpke ?? null,
    dpke_ortalama: dpke.deger?.ortalama ?? null,
    ats_hisse: finra.deger?.atsHisse ?? null,
    ats_hafta: finra.deger?.hafta ?? null,
    hatalar: { qlib: qlib.hata, taa: taa.hata, dpke: dpke.hata, finra: finra.hata },
  }
}

/** Semboller ARASI paralel: sirali olsaydi 8 sembol ~10 saniye surerdi. */
export async function tabloGetir(semboller, secenek = {}) {
  return Promise.all(semboller.map((t) => sembolSatiri(t, secenek)))
}
