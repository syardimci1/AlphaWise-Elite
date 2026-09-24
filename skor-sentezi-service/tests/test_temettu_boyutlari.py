"""
K2-08 — temettu VERIMI ve temettu BUYUMESI rapor boyutlari.

KAPSAM SINIRI (bu dosyanin asil isi)
====================================
Rakipte (Seeking Alpha) temettu icin dort ayri not var: Safety, Yield,
Growth, Consistency. AlphaWise'in temettu ekseni yalnizca DAYANIKLILIGI
olcuyor (odeme orani 0.40 / FCF kapsami 0.40 / kesintisiz sure 0.20).
Eksik iki boyut — verim ve buyume — buraya RAPOR alani olarak eklenir,
PUANA DEGIL. Puana katmak kalibre edilmemis bir agirlik uydurmak olurdu;
bu yuzden asagidaki regresyon testi, yeni alanlarin puana SIZMADIGINI
olcerek kilitler.

Ikinci kural: seri yoksa deger 0 veya "notr" DEGIL, acikca 'olculemedi'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import datetime
import pytest
from src.skorlar import Donem, Sirket, temettu_dayanikligi
from src.olcum import OLCULDU, OLCULEMEDI, UYGULANAMAZ
from src.veri import _temettu_pencereleri
from src.mercek import MERCEK_HARITASI


def temettu_sirketi(temettu=-40.0, ni=100.0, fcf=100.0, yil=10,
                    fiyat=50.0, son12=2.0, onceki12=1.60):
    """test_skorlar.py'deki ayni fikstur + yeni piyasa alanlari.

    odeme orani .40 -> bilesen 100; fcf orani .40 -> 100; 10/20 yil -> 50
    puan = .4*100 + .4*100 + .2*50 = 90
    """
    piyasa = {"temettu_kesintisiz_yil": yil, "fiyat": fiyat,
              "temettu_son12ay": son12, "temettu_onceki12ay": onceki12}
    return Sirket("TEST", [Donem("2026", gelir={"Net Income": ni},
                                 nakit={"Cash Dividends Paid": temettu,
                                        "Free Cash Flow": fcf})],
                  piyasa=piyasa)


# ------------------------------------------------------------------ (1) VARLIK
def test_temettu_odeyende_verim_ve_buyume_KENDI_DURUMUYLA_raporlanir():
    o = temettu_dayanikligi(temettu_sirketi())
    assert o.durum == OLCULDU

    verim = o.ayrinti["verim"]
    assert verim["durum"] == OLCULDU
    assert verim["deger"] == pytest.approx(2.0 / 50.0)      # 0.04

    buyume = o.ayrinti["temettu_buyumesi"]
    assert buyume["durum"] == OLCULDU
    assert buyume["deger"] == pytest.approx(2.0 / 1.60 - 1.0)  # 0.25


def test_yeni_boyutlar_PUANA_GIRMEDIKLERINI_kendileri_bildirir():
    """Kapsam siniri okunabilir olmali: alanin kendisi 'puana girmem' demeli."""
    o = temettu_dayanikligi(temettu_sirketi())
    for ad in ("verim", "temettu_buyumesi"):
        assert o.ayrinti[ad]["puana_girer"] is False, ad


# ------------------------------------------------- (2) OLCULEMEDI != 0, != NOTR
def test_temettu_serisi_YOKKEN_buyume_OLCULEMEDI_doner_sifir_DEGIL():
    """'Olculemedi' ile 'olculdu ve 0' ayrimi bu depoda bir sozlesmedir.
    Buyumeye 0 yazmak 'temettu sabit kaldi' demektir — bambaska bir iddia."""
    o = temettu_dayanikligi(temettu_sirketi(son12=None, onceki12=None))
    assert o.durum == OLCULDU, "seri yoklugu EKSENI dusurmemeli"

    buyume = o.ayrinti["temettu_buyumesi"]
    assert buyume["durum"] == OLCULEMEDI
    assert buyume["deger"] is None, "olculemedi durumunda sayi yazilamaz"
    assert buyume["gerekce"], "olculemedi GEREKCESIZ birakilamaz"

    verim = o.ayrinti["verim"]
    assert verim["durum"] == OLCULEMEDI and verim["deger"] is None


def test_tek_pencere_varken_verim_OLCULUR_ama_buyume_OLCULEMEZ():
    """Iki boyut BAGIMSIZ raporlanir; biri olculemedi diye digeri dusmez."""
    o = temettu_dayanikligi(temettu_sirketi(son12=2.0, onceki12=None))
    assert o.ayrinti["verim"]["durum"] == OLCULDU
    assert o.ayrinti["temettu_buyumesi"]["durum"] == OLCULEMEDI


def test_fiyat_yokken_verim_OLCULEMEDI_doner():
    o = temettu_dayanikligi(temettu_sirketi(fiyat=None))
    assert o.ayrinti["verim"]["durum"] == OLCULEMEDI
    assert o.ayrinti["verim"]["deger"] is None


# --------------------------------------------- (3) MEVCUT DAVRANIS KORUNUR
def test_temettu_odemeyende_eksen_HALA_UYGULANAMAZ():
    """skorlar.py:432 davranisi K2-08 ile DEGISMEZ."""
    s = Sirket("TEST", [Donem("2026", gelir={"Net Income": 100.0},
                              nakit={"Free Cash Flow": 100.0})], piyasa={})
    o = temettu_dayanikligi(s)
    assert o.durum == UYGULANAMAZ and o.deger is None


# ------------------------------------------------------------- (4) REGRESYON
def test_temettu_puani_yeni_boyutlardan_ETKILENMEZ():
    """K2-08'in en kritik testi: verim/buyume degisse de PUAN kipirdamamali.

    Puani yeni boyutlara duyarli kilan her degisiklik burada dusen bir
    testtir — cunku boyle bir degisiklik 0.40/0.40/0.20 agirliklarini
    yeniden bolmek, yani kalibre edilmemis agirlik uydurmak demektir.
    """
    zengin = temettu_dayanikligi(temettu_sirketi(son12=2.0, onceki12=1.60))
    yoksul = temettu_dayanikligi(temettu_sirketi(son12=None, onceki12=None))
    yuksek = temettu_dayanikligi(temettu_sirketi(son12=9.0, onceki12=0.10))

    assert zengin.deger == yoksul.deger == yuksek.deger


def test_temettu_puani_degisiklik_ONCESIYLE_BIREBIR_AYNI():
    """Degisiklik oncesi elle hesaplanmis deger: .4*100 + .4*100 + .2*50 = 90"""
    o = temettu_dayanikligi(temettu_sirketi())
    assert o.deger == pytest.approx(90.0)
    assert o.ayrinti["bilesen_odeme"] == pytest.approx(100.0)
    assert o.ayrinti["bilesen_fcf"] == pytest.approx(100.0)
    assert o.ayrinti["bilesen_sure"] == pytest.approx(50.0)
    # Puan YALNIZCA uc bilesenin agirlikli ortalamasidir.
    assert o.deger == pytest.approx(0.40 * o.ayrinti["bilesen_odeme"]
                                    + 0.40 * o.ayrinti["bilesen_fcf"]
                                    + 0.20 * o.ayrinti["bilesen_sure"])


# ---------------------------------------------------- (5) MERCEK METNI TUTARLI
def test_temettu_mercegi_verim_hakkinda_CELISKILI_konusmaz():
    """/mercekler ucu MERCEKLER listesini yayimlar (main.py:88).

    Verim artik ayrintida RAPORLANDIGI icin, 'bu eksende olculmez' demek
    kendi ciktimizla celisirdi. Korunmasi gereken ayrim: raporlanir ama
    PUANA girmez.
    """
    cumleler = MERCEK_HARITASI["temettu_odakli"]["soyleyemedikleri"]
    verim_cumleleri = [c for c in cumleler if "VERİM" in c.upper()]
    assert verim_cumleleri, "temettu mercegi verim hakkinda hicbir sey demiyor"

    c = verim_cumleleri[0]
    assert "ölçülmez" not in c, (
        "verim artik raporlaniyor; 'olculmez' demek ciktimizla celisiyor")
    assert "raporlan" in c.lower(), "verimin RAPORLANDIGI soylenmeli"
    assert "puan" in c.lower(), "verimin PUANA girmedigi soylenmeli"


# ------------------------------------------------ veri.py pencere cikarimi
class SahteSeri:
    """yfinance dividends Series'inin bu kodun kullandigi kadari.

    Testin pandas'a bagimli olmamasi bilincli: pencere mantigini olcuyoruz,
    pandas'i degil.
    """

    def __init__(self, ciftler):
        self._ciftler = list(ciftler)

    def __len__(self):
        return len(self._ciftler)

    def items(self):
        return iter(self._ciftler)


def _gun(n):
    return datetime.date(2026, 1, 1) - datetime.timedelta(days=n)


def test_pencereler_son_odeme_tarihini_CAPA_alir():
    """Capa bugun DEGIL son odeme tarihidir: ayni seri her kosuda ayni
    sonucu verir (determinizm) ve kismi yil pencereyi bozmaz."""
    seri = SahteSeri([
        (_gun(700), 0.30), (_gun(550), 0.35),   # onceki 12 ay: 0.65
        (_gun(300), 0.40), (_gun(10), 0.50),    # son 12 ay: 0.90
    ])
    son, onceki = _temettu_pencereleri(seri)
    assert son == pytest.approx(0.90)
    assert onceki == pytest.approx(0.65)


def test_pencereler_bos_seride_NONE_doner_sifir_DEGIL():
    for bos in (None, SahteSeri([])):
        son, onceki = _temettu_pencereleri(bos)
        assert son is None and onceki is None


def test_tek_yillik_seride_onceki_pencere_NONE_kalir():
    """Uydurma bir taban (0) buyumeyi sonsuz gosterirdi."""
    seri = SahteSeri([(_gun(200), 0.40), (_gun(20), 0.40)])
    son, onceki = _temettu_pencereleri(seri)
    assert son == pytest.approx(0.80)
    assert onceki is None
