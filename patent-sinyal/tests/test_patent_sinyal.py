"""Patent sinyali testleri — Madde 35.

Testlerin tamami CEVRIMDISIDIR: kaynak sahte bir 'acan' ile taklit edilir.
Boylece testler Google'in hiz sinirina ya da uc noktanin o anki durumuna
bagli olmaz. Gercek uc noktanin cevap verdigi ayrica olculmustur ve denetim
raporunda kayitlidir.
"""
import io
import json
import sys
import urllib.error
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eslesme import anlamli_belirtecler, ortusuyor_mu, sahip_adaylari  # noqa: E402
from kaynak import KaynakHatasi, ornek_kayitlar, sorgu_sayisi  # noqa: E402
from momentum import (VARSAYILAN_OLGUNLUK_AY, _ay_ekle, momentum,  # noqa: E402
                      pencere_sayisi, veri_bitis_tarihi)
from olcum import OLCULDU, OLCULEMEDI  # noqa: E402


# ------------------------------------------------------------- sahte kaynak
class _Yanit(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def acan_govde(govde):
    """Verilen govdeyi dondur."""
    ham = govde if isinstance(govde, bytes) else json.dumps(govde).encode()
    return lambda istek, timeout=None: _Yanit(ham)


def acan_hata(hata):
    def _ac(istek, timeout=None):
        raise hata
    return _ac


def _sonuc(toplam, kayitlar=()):
    return {"results": {"total_num_results": toplam,
                        "cluster": [{"result": [{"patent": k} for k in kayitlar]}]}}


# ------------------------------------------------------------------ kaynak
def test_gecerli_yanit_olculdu():
    o = sorgu_sayisi("q=x", acan=acan_govde(_sonuc(1234)))
    assert o.durum == OLCULDU and o.deger == 1234.0


def test_sifir_sonuc_gercek_olcumdur():
    """0 patent GERCEK bir olcumdur; OLCULEMEDI ile karistirilmamali."""
    o = sorgu_sayisi("q=x", acan=acan_govde(_sonuc(0)))
    assert o.durum == OLCULDU and o.deger == 0.0


def test_http_503_sifir_degil_olculemedi():
    """Gercekte karsilasilan durum: kaynak hiz siniri uyguluyor (503).

    Bunu 0 patent saymak, sirketin yenilik uretmedigi anlamina gelirdi.
    """
    hata = urllib.error.HTTPError("u", 503, "Service Unavailable", {}, None)
    o = sorgu_sayisi("q=x", acan=acan_hata(hata))
    assert o.durum == OLCULEMEDI and o.deger is None
    assert o.ayrinti["kaynak_kirilgan"] is True


def test_http_429_olculemedi():
    hata = urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)
    assert sorgu_sayisi("q=x", acan=acan_hata(hata)).durum == OLCULEMEDI


def test_baglanti_hatasi_olculemedi():
    o = sorgu_sayisi("q=x", acan=acan_hata(urllib.error.URLError("ag yok")))
    assert o.durum == OLCULEMEDI and "ulasilamadi" in o.gerekce


def test_zaman_asimi_olculemedi():
    assert sorgu_sayisi("q=x", acan=acan_hata(TimeoutError())).durum == OLCULEMEDI


def test_html_hata_sayfasi_olculemedi():
    """Google hata sayfasi dondurdugunde HTML gelir — sessizce 0 sayilmamali."""
    o = sorgu_sayisi("q=x", acan=acan_govde(b"<!doctype html><html>Error 500"))
    assert o.durum == OLCULEMEDI and "JSON" in o.gerekce


def test_sema_degisirse_olculemedi():
    o = sorgu_sayisi("q=x", acan=acan_govde({"baska": {}}))
    assert o.durum == OLCULEMEDI and "results" in o.gerekce


def test_results_sozluk_degilse_olculemedi():
    o = sorgu_sayisi("q=x", acan=acan_govde({"results": [1, 2]}))
    assert o.durum == OLCULEMEDI


def test_toplam_alani_yoksa_olculemedi():
    o = sorgu_sayisi("q=x", acan=acan_govde({"results": {"cluster": []}}))
    assert o.durum == OLCULEMEDI and "total_num_results" in o.eksik


@pytest.mark.parametrize("bozuk", ["cok", None, -5, True, [3]])
def test_sayi_olmayan_toplam_olculemedi(bozuk):
    """True bilerek listede: bool int alt sinifidir, sayi sayilmamali."""
    o = sorgu_sayisi("q=x", acan=acan_govde(_sonuc(bozuk)))
    assert o.durum == OLCULEMEDI, f"{bozuk!r} olcum sayildi"


def test_ornek_kayitlar_hatada_bos_liste_degil_firlatir():
    """Bos liste 'sonuc yok' ile karisirdi; hata firlatilmali."""
    with pytest.raises(KaynakHatasi):
        ornek_kayitlar("q=x", acan=acan_hata(urllib.error.URLError("yok")))


def test_ornek_kayitlar_adet_siniri():
    kayitlar = [{"publication_number": f"US{i}", "assignee": "A"} for i in range(50)]
    assert len(ornek_kayitlar("q=x", adet=7, acan=acan_govde(_sonuc(50, kayitlar)))) == 7


# ----------------------------------------------------------------- eslesme
@pytest.mark.parametrize("ad,beklenen", [
    ("Microsoft Technology Licensing, LLC", ("microsoft",)),
    ("Advanced Micro Devices, Inc.", ("advanced", "micro", "devices")),
    ("Google LLC", ("google",)),
    ("The Procter & Gamble Company", ("procter", "gamble")),
    ("", ()),
])
def test_anlamli_belirtecler(ad, beklenen):
    assert anlamli_belirtecler(ad) == beklenen


def test_ortusme_tuzel_ek_farkini_gormezden_gelir():
    assert ortusuyor_mu("Microsoft", "Microsoft Technology Licensing, LLC")
    assert ortusuyor_mu("Google", "GOOGLE LLC")
    assert ortusuyor_mu("Google", "Google Inc.")


def test_ortusme_kismi_eslesmeyi_reddeder():
    """'Apple' ile 'Apple Rush Company' ayni sirket degildir — ama tersi dogru:
    aranan ad daha genelse (Apple) ve donen ad onu iceriyorsa eslesir. Bu
    yuzden ayirt edici testi ters yonde yapiyoruz."""
    assert not ortusuyor_mu("Apple Rush Company", "Apple Inc.")
    assert not ortusuyor_mu("Advanced Micro Devices", "Micro Focus Limited")


def test_ortusme_bos_ad_reddeder():
    assert not ortusuyor_mu("", "Microsoft") and not ortusuyor_mu("LLC Inc", "X")


def test_sahip_adaylari_dogrular():
    kayitlar = [{"assignee": "Microsoft Technology Licensing, LLC"}] * 3 + \
               [{"assignee": "Commvault Systems, Inc."}]
    o = sahip_adaylari("Microsoft", acan=acan_govde(_sonuc(4, kayitlar)))
    assert o.durum == OLCULDU
    assert o.ayrinti["dogrulanan_sahipler"] == ["Microsoft Technology Licensing, LLC"]
    assert len(o.ayrinti["adaylar"]) == 2


def test_sahip_adaylari_sonuc_yoksa_olculemedi():
    """En tehlikeli sessiz hata: eslestirilemedi != patenti yok."""
    o = sahip_adaylari("Bilinmeyen Sirket", acan=acan_govde(_sonuc(0, [])))
    assert o.durum == OLCULEMEDI
    assert "patenti OLMADIGI anlamina GELMEZ" in o.gerekce


def test_sahip_adaylari_ortusen_yoksa_olculemedi():
    kayitlar = [{"assignee": "Bambaska Sirket A.S."}]
    o = sahip_adaylari("Microsoft", acan=acan_govde(_sonuc(1, kayitlar)))
    assert o.durum == OLCULEMEDI and "ortusmuyor" in o.gerekce
    assert o.ayrinti["adaylar"][0]["ortusuyor"] is False


def test_sahip_adaylari_bos_girdi():
    o = sahip_adaylari("   ")
    assert o.durum == OLCULEMEDI and "sirket_adi" in o.eksik


def test_sahip_adaylari_kaynak_hatasinda_olculemedi():
    o = sahip_adaylari("Microsoft", acan=acan_hata(urllib.error.URLError("yok")))
    assert o.durum == OLCULEMEDI and o.ayrinti["kaynak_kirilgan"] is True


# ---------------------------------------------------------------- momentum
@pytest.mark.parametrize("t,ay,beklenen", [
    (date(2026, 9, 10), -24, date(2024, 9, 10)),
    (date(2026, 1, 31), -1, date(2025, 12, 31)),
    (date(2026, 3, 31), -1, date(2026, 2, 28)),   # ay sonu kismasi
    (date(2024, 3, 31), -1, date(2024, 2, 29)),   # artik yil
    (date(2026, 12, 15), 1, date(2027, 1, 15)),   # yil sinirini asma
])
def test_ay_aritmetigi(t, ay, beklenen):
    assert _ay_ekle(t, ay) == beklenen


def test_veri_bitisi_olgunluk_kadar_geride():
    assert veri_bitis_tarihi(date(2026, 9, 10)) == date(2024, 9, 10)
    assert VARSAYILAN_OLGUNLUK_AY == 24


def test_momentum_olgunlasmamis_donemi_hic_sormaz():
    """En kritik test: sorgular veri_bitis_tarihi'ni ASMAMALI.

    Asarsa yayin gecikmesi yuzunden her sirkette sahte dusus uretilir.
    """
    sorulan = []

    def izleyen(istek, timeout=None):
        sorulan.append(urllib.parse.unquote(istek.full_url))
        return _Yanit(json.dumps(_sonuc(100)).encode())

    import urllib.parse
    momentum("Microsoft", date(2026, 9, 10), acan=izleyen)
    assert len(sorulan) == 2
    for u in sorulan:
        for alan in ("after=priority:", "before=priority:"):
            tarih = u.split(alan)[1][:8]
            assert tarih <= "20240910", (
                f"olgunlasmamis donem sorgulandi: {tarih} > 20240910")


def test_momentum_artis():
    sayilar = iter([150, 100])   # once son pencere, sonra onceki
    o = momentum("X", date(2026, 9, 10),
                 acan=lambda i, timeout=None: _Yanit(
                     json.dumps(_sonuc(next(sayilar))).encode()))
    assert o.durum == OLCULDU and o.deger == pytest.approx(1.5)
    assert o.ayrinti["veri_bitis_tarihi"] == "2024-09-10"
    assert "gecikmelidir" in o.ayrinti["gecikme_notu"]


def test_momentum_dusus():
    sayilar = iter([50, 100])
    o = momentum("X", date(2026, 9, 10),
                 acan=lambda i, timeout=None: _Yanit(
                     json.dumps(_sonuc(next(sayilar))).encode()))
    assert o.deger == pytest.approx(0.5)


def test_momentum_onceki_sifirsa_bolme_yapmaz():
    sayilar = iter([10, 0])
    o = momentum("X", date(2026, 9, 10),
                 acan=lambda i, timeout=None: _Yanit(
                     json.dumps(_sonuc(next(sayilar))).encode()))
    assert o.durum == OLCULEMEDI and "sifira bolme" in o.gerekce
    assert o.ayrinti["onceki_adet"] == 0


def test_momentum_her_iki_pencere_sifirsa_olculemedi():
    o = momentum("X", date(2026, 9, 10), acan=acan_govde(_sonuc(0)))
    assert o.durum == OLCULEMEDI


def test_momentum_kaynak_dusunce_olculemedi():
    hata = urllib.error.HTTPError("u", 503, "rate limit", {}, None)
    o = momentum("X", date(2026, 9, 10), acan=acan_hata(hata))
    assert o.durum == OLCULEMEDI and "son pencere olculemedi" in o.gerekce


def test_momentum_ikinci_sorgu_dusunce_olculemedi():
    durum = {"n": 0}

    def yarim(istek, timeout=None):
        durum["n"] += 1
        if durum["n"] == 1:
            return _Yanit(json.dumps(_sonuc(10)).encode())
        raise urllib.error.HTTPError("u", 503, "rate limit", {}, None)

    o = momentum("X", date(2026, 9, 10), acan=yarim)
    assert o.durum == OLCULEMEDI and "onceki pencere olculemedi" in o.gerekce


@pytest.mark.parametrize("pencere,olgunluk", [(0, 24), (-3, 24), (12, -1)])
def test_momentum_gecersiz_parametre(pencere, olgunluk):
    o = momentum("X", date(2026, 9, 10), pencere_ay=pencere, olgunluk_ay=olgunluk)
    assert o.durum == OLCULEMEDI


def test_pencere_sayisi_ters_aralik_reddedilir():
    o = pencere_sayisi("X", date(2025, 1, 1), date(2024, 1, 1))
    assert o.durum == OLCULEMEDI and "gecersiz aralik" in o.gerekce
