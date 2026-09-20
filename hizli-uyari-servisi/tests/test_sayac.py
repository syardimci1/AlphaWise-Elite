import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _temiz_sayac(tmp_path, monkeypatch, limit=3):
    monkeypatch.setenv("SAYAC_DOSYA_YOLU", str(tmp_path / "sayac.json"))
    monkeypatch.setenv("GUNLUK_ISTEK_LIMITI", str(limit))
    from src import sayac
    importlib.reload(sayac)
    return sayac


def test_limit_altinda_izin_verir(tmp_path, monkeypatch):
    sayac = _temiz_sayac(tmp_path, monkeypatch, limit=3)
    sonuc = sayac.istek_izni_al()
    assert sonuc["kullanilan"] == 1
    assert sonuc["limit"] == 3


def test_limit_asilinca_hata_firlatir(tmp_path, monkeypatch):
    sayac = _temiz_sayac(tmp_path, monkeypatch, limit=2)
    sayac.istek_izni_al()
    sayac.istek_izni_al()
    try:
        sayac.istek_izni_al()
        assert False, "GunlukLimitAsildi firlatilmaliydi"
    except sayac.GunlukLimitAsildi:
        pass


def test_durum_dosya_yokken_sifir_doner(tmp_path, monkeypatch):
    sayac = _temiz_sayac(tmp_path, monkeypatch, limit=5)
    d = sayac.durum()
    assert d["kullanilan"] == 0
    assert d["limit"] == 5
