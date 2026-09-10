"""Borsa disi baski payi testleri — madde 40.

ASENKRON TESTLER pytest-asyncio ILE DEGIL, asyncio.run ILE KOSAR.
Ilk yazimda @pytest.mark.asyncio kullanildi ve eklenti kurulu olmadigi
icin 12 testin 12'si SESSIZCE ATLANDI - yani hicbir sey korumuyorlardi.
Yeni bir bagimlilik eklemek yerine testler senkron yazildi; boylece
atlanmalari mumkun degil.

Agirlik, ORANIN KENDISINDE degil, olculemeyen gunlerin nasil ele
alindigindadir: iki kaynak farkli sistemlerden geldigi icin gun gun
eslesmeyebilir ve eslesmeyen gunleri sessizce atmak, ortalamayi
okuyucunun bilmedigi bir alt kumeden hesaplamak demektir.
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, "/app")

from src import baski  # noqa: E402
from src.baski import OLCULDU, OLCULEMEDI, TUTARSIZ  # noqa: E402


# ------------------------------------------------------------- _gun_kaydi
def test_normal_gun_olculur():
    k = baski._gun_kaydi(date(2026, 9, 3), 9_637_447.0, 24_111_400.0, "")
    assert k["durum"] == OLCULDU
    assert k["pay_yuzde"] == pytest.approx(39.97, abs=0.01)


def test_konsolide_yoksa_OLCULEMEDI_sifir_degil():
    k = baski._gun_kaydi(date(2026, 9, 9), 4_914_333.98, None, "")
    assert k["durum"] == OLCULEMEDI
    assert k["pay_yuzde"] is None, "olculemeyen gun sifir pay olarak yazilamaz"
    assert k["borsa_disi_hacim"] == 4_914_333.98, (
        "olculebilen taraf yine de raporlanmali")


def test_konsolide_yoksa_gerekce_tasinir():
    k = baski._gun_kaydi(date(2026, 9, 9), 100.0, None,
                         "market-data-service HTTP 503")
    assert "503" in k["gerekce"]


def test_konsolide_yoksa_gerekce_uretilir():
    k = baski._gun_kaydi(date(2026, 9, 9), 100.0, None, "")
    assert "2026-09-09" in k["gerekce"]


@pytest.mark.parametrize("kons", [0.0, -5.0])
def test_sifir_konsolide_bolme_yapmaz(kons):
    k = baski._gun_kaydi(date(2026, 9, 3), 100.0, kons, "")
    assert k["durum"] == OLCULEMEDI and k["pay_yuzde"] is None


def test_yuzden_buyuk_oran_TUTARSIZ_ve_kirpilmaz():
    """Kirpmak, iki kaynagin ayni seyi olcmedigi gercegini gizlerdi."""
    k = baski._gun_kaydi(date(2026, 9, 3), 200.0, 100.0, "")
    assert k["durum"] == TUTARSIZ
    assert k["pay_yuzde"] == 200.0, "deger kirpilmamali, oldugu gibi gosterilmeli"
    assert "KATILMADI" in k["gerekce"]


def test_tam_yuz_tutarsiz_SAYILMAZ():
    """Sinir: %100 mumkun (tum hacim borsa disi bildirilmisse)."""
    k = baski._gun_kaydi(date(2026, 9, 3), 100.0, 100.0, "")
    assert k["durum"] == OLCULDU and k["pay_yuzde"] == 100.0


def test_sifir_borsa_disi_gercek_olcumdur():
    k = baski._gun_kaydi(date(2026, 9, 3), 0.0, 1000.0, "")
    assert k["durum"] == OLCULDU and k["pay_yuzde"] == 0.0


# ------------------------------------------------- _konsolide_hacimler
class _Yanit:
    def __init__(self, kod=200, govde=None, patlat=False):
        self.status_code = kod
        self._g = govde
        self._patlat = patlat

    def json(self):
        if self._patlat:
            raise ValueError("JSON degil")
        return self._g


class _Istemci:
    def __init__(self, yanit=None, hata=None):
        self._y, self._h = yanit, hata

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        if self._h:
            raise self._h
        return self._y


def _kur(monkeypatch, yanit=None, hata=None):
    monkeypatch.setattr(baski.httpx, "AsyncClient",
                        lambda *a, **k: _Istemci(yanit, hata))


def test_konsolide_okunur(monkeypatch):
    _kur(monkeypatch, _Yanit(200, {"data": [
        {"date": "2026-09-03", "volume": "24111400"},
        {"date": "2026-09-02", "volume": "15336100"}]}))
    h, g = asyncio.run(baski._konsolide_hacimler("MSFT"))
    assert h == {"2026-09-03": 24111400.0, "2026-09-02": 15336100.0} and g == ""


def test_konsolide_ag_hatasi_gerekce_verir(monkeypatch):
    _kur(monkeypatch, hata=OSError("ag yok"))
    h, g = asyncio.run(baski._konsolide_hacimler("MSFT"))
    assert h == {} and "ulasilamadi" in g


def test_konsolide_http_hatasi_gerekce_verir(monkeypatch):
    _kur(monkeypatch, _Yanit(503))
    h, g = asyncio.run(baski._konsolide_hacimler("MSFT"))
    assert h == {} and "503" in g


def test_konsolide_error_alanli_200_yanit_kabul_EDILMEZ(monkeypatch):
    """Bu depoda servisler HTTP 200 ile birlikte error alani dondurebiliyor."""
    _kur(monkeypatch, _Yanit(200, {"error": "ticker bulunamadi"}))
    h, g = asyncio.run(baski._konsolide_hacimler("YOKBOYLE"))
    assert h == {} and "ticker bulunamadi" in g


def test_konsolide_bozuk_json_gerekce_verir(monkeypatch):
    _kur(monkeypatch, _Yanit(200, patlat=True))
    h, g = asyncio.run(baski._konsolide_hacimler("MSFT"))
    assert h == {} and "JSON" in g


def test_konsolide_bos_veri_gerekce_verir(monkeypatch):
    _kur(monkeypatch, _Yanit(200, {"data": []}))
    h, g = asyncio.run(baski._konsolide_hacimler("MSFT"))
    assert h == {} and "hacim icermeyen" in g


def test_sifir_ve_bozuk_hacimler_atlanir(monkeypatch):
    _kur(monkeypatch, _Yanit(200, {"data": [
        {"date": "2026-09-03", "volume": "0"},
        {"date": "2026-09-02", "volume": "abc"},
        {"date": "2026-09-01", "volume": None},
        {"date": "2026-08-31", "volume": "100"}]}))
    h, g = asyncio.run(baski._konsolide_hacimler("MSFT"))
    assert h == {"2026-08-31": 100.0}


# ------------------------------------------------------- borsa_disi_pay
def _sahte_gun_dosyasi(veriler):
    async def _f(g):
        return veriler.get(g.isoformat())
    return _f


def test_ortalama_yalnizca_olculen_gunlerden(monkeypatch):
    """Eslesmeyen gunler ortalamayi BOZMAMALI ama gizlenmemeli de."""
    bugun = date.today()
    gunler = {}
    g, n = bugun, 0
    tarihler = []
    while n < 4:
        g = g.fromordinal(g.toordinal() - 1)
        if g.weekday() >= 5:
            continue
        n += 1
        tarihler.append(g)
        gunler[g.isoformat()] = {"MSFT": (0.0, 0.0, 1000.0)}
    monkeypatch.setattr(baski, "_gun_dosyasi", _sahte_gun_dosyasi(gunler))
    # yalnizca ILK IKI gun icin konsolide hacim var
    kons = {tarihler[0].isoformat(): 2000.0, tarihler[1].isoformat(): 4000.0}

    async def _kh(t):
        return kons, ""
    monkeypatch.setattr(baski, "_konsolide_hacimler", _kh)

    r = asyncio.run(baski.borsa_disi_pay("MSFT", gun=4))
    assert r["gun_sayisi"] == 4
    assert r["olculen_gun"] == 2 and r["olculemeyen_gun"] == 2
    assert r["ortalama_pay_yuzde"] == pytest.approx(37.5), "(50 + 25) / 2"
    assert r["en_yeni_pay_yuzde"] == 50.0


def test_tutarsiz_gun_ortalamaya_KATILMAZ(monkeypatch):
    bugun = date.today()
    gunler, tarihler = {}, []
    g, n = bugun, 0
    while n < 2:
        g = g.fromordinal(g.toordinal() - 1)
        if g.weekday() >= 5:
            continue
        n += 1
        tarihler.append(g)
    gunler[tarihler[0].isoformat()] = {"X": (0.0, 0.0, 5000.0)}   # tutarsiz
    gunler[tarihler[1].isoformat()] = {"X": (0.0, 0.0, 1000.0)}   # normal
    monkeypatch.setattr(baski, "_gun_dosyasi", _sahte_gun_dosyasi(gunler))

    async def _kh(t):
        return {tarihler[0].isoformat(): 1000.0,
                tarihler[1].isoformat(): 2000.0}, ""
    monkeypatch.setattr(baski, "_konsolide_hacimler", _kh)

    r = asyncio.run(baski.borsa_disi_pay("X", gun=2))
    assert r["tutarsiz_gun"] == 1 and r["olculen_gun"] == 1
    assert r["ortalama_pay_yuzde"] == pytest.approx(50.0), (
        "tutarsiz gun (500%) ortalamaya girmis olabilir")


def test_hicbir_gun_olculemezse_ortalama_None(monkeypatch):
    """Sifir degil None: 'olculemedi' ile 'pay sifir' ayni sey degil."""
    bugun = date.today()
    g = bugun.fromordinal(bugun.toordinal() - 1)
    while g.weekday() >= 5:
        g = g.fromordinal(g.toordinal() - 1)
    monkeypatch.setattr(baski, "_gun_dosyasi",
                        _sahte_gun_dosyasi({g.isoformat(): {"X": (0.0, 0.0, 1.0)}}))

    async def _kh(t):
        return {}, "market-data-service'e ulasilamadi: OSError"
    monkeypatch.setattr(baski, "_konsolide_hacimler", _kh)

    r = asyncio.run(baski.borsa_disi_pay("X", gun=1))
    assert r["ortalama_pay_yuzde"] is None
    assert r["en_yeni_pay_yuzde"] is None
    assert r["olculen_gun"] == 0 and r["olculemeyen_gun"] == 1
    assert "ulasilamadi" in r["gunler"][0]["gerekce"]


def test_yayimlanmamis_gun_kayit_URETMEZ(monkeypatch):
    """FINRA dosyasi yoksa o gun 'olculemedi' bile degildir - hic yoktur."""
    monkeypatch.setattr(baski, "_gun_dosyasi", _sahte_gun_dosyasi({}))

    async def _kh(t):
        return {}, ""
    monkeypatch.setattr(baski, "_konsolide_hacimler", _kh)
    r = asyncio.run(baski.borsa_disi_pay("X", gun=5, geriye_bak=8))
    assert r["gun_sayisi"] == 0 and r["ortalama_pay_yuzde"] is None


def test_yon_iddiasi_tasimadigi_bildirilir(monkeypatch):
    monkeypatch.setattr(baski, "_gun_dosyasi", _sahte_gun_dosyasi({}))

    async def _kh(t):
        return {}, ""
    monkeypatch.setattr(baski, "_konsolide_hacimler", _kh)
    r = asyncio.run(baski.borsa_disi_pay("X", gun=1))
    assert r["kalibrasyon_gecerli"] is False
    assert "YON IDDIASI" in r["not"]
