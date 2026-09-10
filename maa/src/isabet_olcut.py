"""Karar isabeti olcutleri — DUZELTILMIS surum (madde 47).

BU MODUL KORUNAN main.py'YE DOKUNMAZ
====================================
maa/src/main.py icindeki evaluate_decisions() ve yazdigi was_correct
alani OLDUGU GIBI KALIR. Bu modul ONUN YANINA ikinci bir degerlendirme
kurar ve ayri sutunlara yazar. Boylece:
  - mevcut gecmis (was_correct) bozulmaz,
  - iki olcut yan yana karsilastirilabilir,
  - korunan dosya kurali cignenmemis olur.

NEDEN IKINCI BIR OLCUT GEREKTI
==============================
Mevcut kural (main.py'de, degistirilmedi):
    EKLE      dogru  <=  getiri > 0
    DIKKAT ET dogru  <=  getiri < 0
    TUT       dogru  <=  |getiri| < %15
    BEKLE     hic degerlendirilmez (was_correct = None)

TUT'un +-%15 bandi bilgi tasimiyor: kosul KENDILIGINDEN saglaniyor.

OLCUM (10.09.2026, DUZELTILMIS)
===============================
Taban oranlari, decision_log'un GERCEK KARAR EVRENINDE olculdu:
ASML, CAT, GOOGL, JEPI, LLY, NVDA, O, SCHD, TSM, WDC — depodaki tam
gunluk gecmis (2020-2026), 30 barlik ufuk, n=16.367 pencere, piyasa
vekili SPY.

    esik     MUTLAK |r|    GORELI |r - r_SPY|
    %3         %27,3            %32,1
    %5         %41,7            %47,7      <-- secilen
    %6         %47,9            %54,4
    %10        %65,7            %73,0
    %15        %79,9            %87,0

ILK OLCUMUM YANLISTI — KAYDA GECIYOR
====================================
Bu modulun ilk surumunde "mutlak %75,9 / goreli %58,4" yaziyordu. Iki
hata vardi ve ikisi de sonucu sistemin LEHINE bozuyordu:

  1. YANLIS EVREN. Taban, kararlarin gercekten verildigi 10 sembol
     yerine genel bir buyuk-sirket listesiyle (MSFT, AAPL, META, TSLA...)
     olculmustu. Karar evreni farkli davraniyor.
  2. YANLIS PENCERE. Seri market-data'nin /price ucundan alinmisti ve o
     uc VARSAYILAN 60 bar donuyor. 30 barlik ufukla bu, sembol basina
     30 TAMAMEN ORTUSEN pencere demek - "630 gozlem" bagimsiz degildi.

Somut zarari: taban 0,584 verildiginde 13/15 dogru bir TUT sayimi
"tabanin ustunde" (yani BECERI) diye yargilaniyor; dogru taban (0,730)
verildiginde ayni sayim "sanstan ayirt edilemedi" cikiyor. Ayni veriden
zit iki yargi.

Bu yuzden asagidaki taban degerleri artik bir TESTLE veriden yeniden
hesaplanip dogrulaniyor (test_isabet_taban.py); docstring bir daha
sessizce eskiyemez.

SECILEN OLCUT: PIYASAYA GORELI +-%5
===================================
    TUT dogru  <=  |hisse getirisi - piyasa getirisi| < %5
Olculen taban: %47,7 — yani yazi-tura referansina en yakin esik.

Mutlak bant yerine goreli bant secildi cunku mutlak bant TUT'u DUZ BIR
PIYASADA kendiliginden odullendirir: tum piyasa %20 duserken TUT karari
makul olabilir ama mutlak olcut onu "yanlis" sayar.

BEKLE DEGERLENDIRILMEZ — AMA NEDENI YAZILIR
===========================================
BEKLE, gecerli katman sayisi 3'un altina dustugunde uretilir; yani
"OLCEMEDIK" demektir. Fiyat hareketine bakip dogru/yanlis demek,
olculemedi'yi bir piyasa cagrisina cevirir - bu depoda 232d1a0 ile
kapatilan hatanin ta kendisi. Bu yuzden BEKLE 'uygulanamaz' olarak
isaretlenir. Mevcut durumda was_correct = None yaziliyor ve bu
"henuz degerlendirilmedi" ile AYIRT EDILEMIYOR; yeni alan ikisini ayirir.

EKLE ve DIKKAT ET DEGISMEDI
===========================
Ikisinin olcutu de olculdu ve bilgi tasidiklari gorulda (ayni evrende
r > 0 tabani ve r < 0 tabani yazi tura civarinda, yani ayirt edici). Bu
maddenin kapsami TUT ve BEKLE idi; calisan bir olcutu gereksiz yere
degistirmek, eski degerlendirmeyle karsilastirilabilirligi de bozardi.
"""
from __future__ import annotations

# Piyasaya goreli TUT bandi.
# Olculen taban: %47,7 (gercek karar evreni, 16.367 pencere, SPY, tam gecmis).
# Bu deger test_isabet_taban.py tarafindan VERIDEN yeniden hesaplanip
# dogrulanir; elle degistirilirse test kirilir.
TUT_GORELI_ESIK = 0.05
TUT_GORELI_TABAN = 0.477

DOGRU = "dogru"
YANLIS = "yanlis"
UYGULANAMAZ = "uygulanamaz"
OLCULEMEDI = "olculemedi"

# Anayasa v4.4 karar kodlari. Bunlarin disindaki kodlar (BELIRSIZ,
# risk_on gibi) bir piyasa cagrisi DEGILDIR ve puanlanmaz.
ANAYASA_KODLARI = ("EKLE", "TUT", "BEKLE", "DIKKAT ET")


def _sonuc(durum, gerekce=""):
    return {"sonuc": durum, "gerekce": gerekce}


def karar_degerlendir(karar, getiri, piyasa_getirisi=None,
                      esik: float = TUT_GORELI_ESIK) -> dict:
    """Bir karari degerlendirir.

    getiri          : karar aninden degerlendirme anina hisse getirisi (kesir)
    piyasa_getirisi : AYNI pencerede piyasa vekilinin getirisi (kesir)

    Doner: {"sonuc": dogru|yanlis|uygulanamaz|olculemedi, "gerekce": ...}
    """
    if karar not in ANAYASA_KODLARI:
        return _sonuc(UYGULANAMAZ,
                      f"'{karar}' Anayasa v4.4 karar kodu degil; bir piyasa "
                      f"cagrisi olmadigi icin puanlanmaz")

    if karar == "BEKLE":
        return _sonuc(UYGULANAMAZ,
                      "BEKLE, gecerli katman sayisi 3'un altina dustugunde "
                      "uretilir; yani 'olcemedik' demektir. Fiyat hareketine "
                      "gore dogru/yanlis demek, olculemedi'yi bir piyasa "
                      "cagrisina cevirirdi.")

    if getiri is None:
        return _sonuc(OLCULEMEDI, "getiri bilinmiyor")
    try:
        getiri = float(getiri)
    except (TypeError, ValueError):
        return _sonuc(OLCULEMEDI, f"getiri sayiya cevrilemedi: {getiri!r}")

    if karar == "EKLE":
        return _sonuc(DOGRU if getiri > 0 else YANLIS,
                      "olcut: getiri > 0 (DEGISMEDI)")
    if karar == "DIKKAT ET":
        return _sonuc(DOGRU if getiri < 0 else YANLIS,
                      "olcut: getiri < 0 (DEGISMEDI)")

    # TUT — piyasaya goreli
    if piyasa_getirisi is None:
        return _sonuc(OLCULEMEDI,
                      "TUT olcutu piyasa getirisi gerektiriyor; piyasa vekili "
                      "bu pencerede okunamadi. Sifir varsaymak, duz bir piyasa "
                      "varsaymak olurdu.")
    try:
        piyasa_getirisi = float(piyasa_getirisi)
    except (TypeError, ValueError):
        return _sonuc(OLCULEMEDI,
                      f"piyasa getirisi sayiya cevrilemedi: {piyasa_getirisi!r}")
    if esik <= 0:
        return _sonuc(OLCULEMEDI, f"esik pozitif olmali: {esik}")
    sapma = abs(getiri - piyasa_getirisi)
    return _sonuc(DOGRU if sapma < esik else YANLIS,
                  f"olcut: |getiri - piyasa| < {esik:.0%} "
                  f"(sapma {sapma:.2%})")


def pencere_gecerli_mi(gun: int, asgari: int = 20) -> dict:
    """Degerlendirme penceresi anlamli mi?

    OLCULEN HATA: decision_log'daki id=2 kaydinin penceresi SIFIR GUN
    (karar ve degerlendirme ayni gun). Boyle bir kaydin getirisi karar
    hakkinda hicbir sey soylemez ama 'dogru' olarak isaretlenmisti.
    """
    if gun is None:
        return _sonuc(OLCULEMEDI, "pencere uzunlugu bilinmiyor")
    if gun < asgari:
        return _sonuc(OLCULEMEDI,
                      f"degerlendirme penceresi {gun} gun; anlamli bir sonuc "
                      f"icin en az {asgari} gun gerekli")
    return _sonuc(DOGRU, "")
