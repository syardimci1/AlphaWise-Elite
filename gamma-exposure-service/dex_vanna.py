"""
DEX (delta maruziyeti) ve VANNA maruziyeti — 23.08.2026.

=== NEDEN AYRI BIR VERI KAYNAGI ===
Gorev metni "mevcut gamma-exposure-service'in ZATEN sahip oldugu FlashAlpha
opsiyon zinciri verisinden hesaplanabilir" diyordu. OLCTUK, bu DOGRU DEGIL:
  * main.py FlashAlpha yanitini HIC ayristirmiyor; `"gex": veri` diye opak
    geciriyor. `grep -rnE 'strike|open_interest|delta|iv'` -> 0 eslesme.
  * Kontrat bazli veri hicbir yerde saklanmiyor; hesaplanacak alan YOK.
  * Ustelik ucretsiz FlashAlpha planinda /gex HTTP 402 donuyor ve BASARISIZ
    CAGRI BILE gunluk kotadan dusuyor (olculdu: 25 -> 24).

COZUM: zincir, zaten kurulu olan openbb-service'ten `yfinance` saglayicisiyla
alinir. UCRETSIZ, ANAHTARSIZ ve FlashAlpha kotasina HIC DOKUNMAZ.
Olculen kapsam (AAPL): 2.418 kontrat, 20 vade, open_interest ve IV'de %0 NaN.

=== YUNANLAR ===
yfinance zincirinde delta/gamma/vega YOK; Black-Scholes ile hesaplanir.
Temettu getirisi q ve risksiz faiz r disaridan verilir (varsayilanlar
yapilandirilabilir); delta ve vanna bu ikisine gore az duyarlidir, ancak
varsayim yanitta ACIKCA dondurulur.

    d1 = [ln(S/K) + (r - q + s^2/2)T] / (s*sqrt(T))
    d2 = d1 - s*sqrt(T)
    delta_call = e^{-qT} N(d1)          delta_put = -e^{-qT} N(-d1)
    gamma      = e^{-qT} f(d1) / (S s sqrt(T))        (call = put)
    vanna      = -e^{-qT} f(d1) d2 / s                 (call = put)
      (vanna = d(delta)/d(sigma) = d(vega)/d(spot))

=== TOPLAMA SOZLESMESI (ACIKCA BELIRTILIR) ===
SqueezeMetrics GEX beyaz kagidi ve projenin CONSTITUTION.md'sinde referans
verilen jensolson/SPX-Gamma-Exposure deposunun sozlesmesi kullanilir:
BAYI (dealer) call'larda UZUN, put'larda KISA kabul edilir; yani
    GEX = SUM(call gamma) - SUM(put gamma)
Bu bir VARSAYIMDIR, olculmus bir gercek DEGILDIR; gercek bayi konumlanmasi
kamuya acik degildir.

23.08.2026 DUZELTME: ilk surum isareti TERS uygulamis (call -, put +) ve
docstring'inde bunu "yaygin kamu varsayimi" diye tanimlamisti. Cekismeli
inceleme bunu gercek SPY zinciriyle yakaladi: cikti her kamu GEX grafiginin
tam TERSI isarette geliyordu ve "negatif gamma" okumasi tersine donuyordu.
  DEX  = SUM( isaret * delta_i * OI_i * 100 * S )        [dolar]
  VEX  = SUM( isaret * vanna_i * OI_i * 100 * S * 0.01 ) [1 puanlik IV icin]
Hem "ham" (isaretsiz) hem "bayi_varsayimli" degerler AYRI dondurulur ki
kullanici hangi varsayimin sonucu ne kadar degistirdigini gorebilsin.

=== KALIBRASYON ===
Bu sinyal bu sistemde KALIBRE EDILMEMISTIR; yon kodu uretmez (lambda = 0).
"""
import math
import os
from datetime import date, datetime

OPENBB_URL = os.getenv("OPENBB_URL", "http://openbb:8000")
RISKSIZ_FAIZ = float(os.getenv("DEX_RISKSIZ_FAIZ", "0.04"))
TEMETTU_GETIRISI = float(os.getenv("DEX_TEMETTU", "0.0"))
KALIBRASYON_GECERLI = False

# Uc degerler hesabi bozmasin diye makul siniflar
MIN_IV, MAKS_IV = 0.01, 5.0
MIN_T_YIL = 1.0 / 365.0 / 24.0 / 6.0   # 10 dakika (gun ici cozunurluk var)


def _N(x: float) -> float:
    """Standart normal birikimli dagilim."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _phi(x: float) -> float:
    """Standart normal yogunluk."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def yunanlar(S: float, K: float, T: float, s: float, tip: str,
             r: float = RISKSIZ_FAIZ, q: float = TEMETTU_GETIRISI) -> dict | None:
    """Tek kontrat icin Black-Scholes delta / gamma / vanna."""
    if not (S > 0 and K > 0 and T >= MIN_T_YIL and MIN_IV <= s <= MAKS_IV):
        return None
    kok = s * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * s * s) * T) / kok
    d2 = d1 - kok
    disk = math.exp(-q * T)
    delta = disk * _N(d1) if tip == "call" else -disk * _N(-d1)
    gamma = disk * _phi(d1) / (S * kok)
    vanna = -disk * _phi(d1) * d2 / s
    return {"delta": delta, "gamma": gamma, "vanna": vanna, "d1": d1, "d2": d2}


# ABD hisse opsiyonlari 16:00 ET'de sona erer. Konteyner UTC calisiyor
# (olculdu: TZ tanimsiz, tzname=('UTC','UTC')); 16:00 ET = 20:00 UTC (EDT) /
# 21:00 UTC (EST). Yaz saatini varsayiyoruz; hatanin etkisi bir saattir ve
# yalnizca vade gunu kapanisa yakin anlamlidir.
VADE_SAATI_UTC = 20.0
GUN_YIL = 365.0


def _yil_kesri(vade, bugun: date | None = None,
               simdi: datetime | None = None) -> float:
    """Vadeye kalan sureyi YIL cinsinden, GUN ICI cozunurlukle dondurur.

    23.08.2026 DUZELTME: onceki surum `max((vade-bugun).days,0)/365` idi.
    Cozunurlugu GUN oldugu icin vadesi BUGUN olan (0DTE) kontratlar T=0
    aliyor, yunanlar() esigine takiliyor ve SESSIZCE dusuyordu — ustelik
    gamma'nin en buyuk oldugu vade tam olarak budur. Gercek SPY zincirinde
    en yakin vade tek basina ham GEX'in %10,3'unu uretiyordu.
    Artik kalan sure saat cozunurlugunde hesaplanir.

    Gecersiz/eksik vade icin -1.0 doner (cagiran taraf kontrati atlar);
    ISTISNA FIRLATMAZ — onceki surum burada tum istegi cokertiyordu.
    """
    try:
        if vade is None:
            return -1.0
        if isinstance(vade, datetime):
            v = vade.date()
        elif isinstance(vade, date):
            v = vade
        elif isinstance(vade, str):
            v = datetime.fromisoformat(vade[:10]).date()
        else:
            return -1.0
    except (TypeError, ValueError):
        return -1.0

    if simdi is None:
        simdi = datetime.utcnow()
    if bugun is not None:
        # Test/tekrarlanabilirlik icin: verilen gunun acilisini taban al
        simdi = datetime(bugun.year, bugun.month, bugun.day)
    saat = simdi.hour + simdi.minute / 60.0
    kalan_gun = (v - simdi.date()).days + (VADE_SAATI_UTC - saat) / 24.0
    return max(kalan_gun, 0.0) / GUN_YIL


def maruziyet_hesapla(kontratlar: list[dict], spot: float,
                      r: float = RISKSIZ_FAIZ, q: float = TEMETTU_GETIRISI,
                      bugun: date | None = None) -> dict:
    """Zincirden DEX / GEX / VEX(vanna) toplar.

    kontratlar: her biri strike, expiration, option_type, open_interest,
    implied_volatility iceren sozlukler.
    """
    ham = {"dex": 0.0, "gex": 0.0, "vex": 0.0}
    bayi = {"dex": 0.0, "gex": 0.0, "vex": 0.0}
    call_dex = put_dex = 0.0
    kullanilan = atlanan = 0
    toplam_oi = 0.0
    # 23.08.2026: atlanan kontratlar TEK sayacta toplaniyordu; OI=0 tamamen
    # NORMAL bir durumken gercek veri hatasiyla ayni kovadaydi ve
    # atlanan_kontrat bir kalite metrigi olarak kullanilamiyordu.
    neden = {"bozuk_alan": 0, "acik_pozisyon_yok": 0, "gecersiz_tip": 0,
             "gecersiz_vade": 0, "gecersiz_iv_veya_vade": 0}
    strike_kirilim: dict[float, float] = {}
    strike_ham: dict[float, float] = {}

    for k in kontratlar:
        # 23.08.2026 DUZELTME: _yil_kesri ONCEDEN bu try blogunun DISINDAYDI;
        # bozuk/eksik bir expiration tek kontrati atlamak yerine TUM istegi
        # cokertiyordu (None/''/epoch degerleriyle dogrulandi).
        try:
            K = float(k["strike"])
            ham_oi = k.get("open_interest")
            oi = float(ham_oi) if ham_oi is not None else 0.0
            s = float(k.get("implied_volatility") or 0.0)
            tip = str(k.get("option_type", "")).lower()
            T = _yil_kesri(k.get("expiration"), bugun)
        except (TypeError, ValueError, KeyError):
            neden["bozuk_alan"] += 1
            atlanan += 1
            continue
        # 23.08.2026 DUZELTME: NaN OI, `oi <= 0` kontrolunu GECIYORDU
        # (IEEE-754: NaN ile her karsilastirma False) ve tum toplamlari
        # sessizce NaN'a ceviriyordu. Acikca elenir.
        if oi != oi or oi <= 0:
            neden["acik_pozisyon_yok"] += 1
            atlanan += 1
            continue
        if tip not in ("call", "put"):
            neden["gecersiz_tip"] += 1
            atlanan += 1
            continue
        if T < 0:
            neden["gecersiz_vade"] += 1
            atlanan += 1
            continue
        g = yunanlar(spot, K, T, s, tip, r, q)
        if g is None:
            neden["gecersiz_iv_veya_vade"] += 1
            atlanan += 1
            continue

        kullanilan += 1
        toplam_oi += oi
        carpan = oi * 100.0
        d_dolar = g["delta"] * carpan * spot
        gm_dolar = g["gamma"] * carpan * spot * spot * 0.01
        vn_dolar = g["vanna"] * carpan * spot * 0.01

        ham["dex"] += d_dolar
        ham["gex"] += gm_dolar
        ham["vex"] += vn_dolar

        # Bayi varsayimi: call'da UZUN (+), put'ta KISA (-)
        # (SqueezeMetrics / jensolson sozlesmesi — bkz. modul docstring'i)
        isaret = 1.0 if tip == "call" else -1.0
        bayi["dex"] += isaret * d_dolar
        bayi["gex"] += isaret * gm_dolar
        bayi["vex"] += isaret * vn_dolar

        if tip == "call":
            call_dex += d_dolar
        else:
            put_dex += d_dolar
        strike_kirilim[K] = strike_kirilim.get(K, 0.0) + isaret * gm_dolar
        strike_ham[K] = strike_ham.get(K, 0.0) + gm_dolar

    en_buyuk = sorted(strike_kirilim.items(), key=lambda x: -abs(x[1]))[:5]
    en_buyuk_ham = sorted(strike_ham.items(), key=lambda x: -x[1])[:5]
    toplam_kontrat = kullanilan + atlanan
    return {
        "spot": spot,
        "kullanilan_kontrat": kullanilan,
        "atlanan_kontrat": atlanan,
        "atlanma_nedeni": neden,
        "atlanma_orani_yuzde": (round(atlanan / toplam_kontrat * 100, 2)
                                if toplam_kontrat else None),
        # 23.08.2026: kullanilan_kontrat=0 iken tum toplamlar 0.0 donuyor ve
        # "gamma yok" ile "veri yok" ayirt edilemiyordu; ustelik bu deger
        # 15 dakika onbellege yaziliyordu. Artik acik bir bayrak var.
        "veri_yetersiz": kullanilan == 0,
        "toplam_acik_pozisyon": toplam_oi,
        "ham": {k: round(v, 2) for k, v in ham.items()},
        "bayi_varsayimli": {k: round(v, 2) for k, v in bayi.items()},
        "call_dex": round(call_dex, 2),
        "put_dex": round(put_dex, 2),
        # DIKKAT: bu liste BAYI-ISARETLI GEX'e gore siralanir; ayni strike'taki
        # call ve put gamma'lari ozdes oldugu icin birbirini goturebilir ve
        # gercek gamma YOGUNLASMASI listeden dusebilir. Bu yuzden isaretsiz
        # (ham) yogunlasma AYRICA dondurulur.
        "en_buyuk_gex_strike_bayi_isaretli": [
            {"strike": s_, "gex": round(v, 2)} for s_, v in en_buyuk],
        "en_buyuk_gamma_yogunlasmasi_ham": [
            {"strike": s_, "gex": round(v, 2)} for s_, v in en_buyuk_ham],
        "varsayimlar": {
            "risksiz_faiz": r,
            "temettu_getirisi": q,
            "bayi_konumu": ("call'da UZUN, put'ta KISA — SqueezeMetrics/jensolson sozlesmesi. VARSAYIMDIR, olculmus degildir."),
            "vex_birimi": "1 puanlik (0.01) IV degisimi basina dolar",
            "gex_birimi": "%1 spot degisimi basina dolar",
        },
        "kalibrasyon_gecerli": KALIBRASYON_GECERLI,
        "yon_kodu_uretir": False,
        "not": ("DEX/GEX/VEX olgusal turevlerdir. Bayi konumlanmasi kamuya acik "
                "olmadigi icin isaret sozlesmesi bir VARSAYIMDIR; 'ham' degerler "
                "varsayimsizdir. Bu sinyal bu sistemde KALIBRE EDILMEMISTIR ve "
                "karar koduna baglanmaz."),
    }
