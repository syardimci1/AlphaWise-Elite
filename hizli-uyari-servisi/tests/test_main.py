import os
import sys
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _istemci(monkeypatch, tmp_path, aktif="false"):
    monkeypatch.setenv("HIZLI_UYARI_AKTIF", aktif)
    monkeypatch.setenv("SAYAC_DOSYA_YOLU", str(tmp_path / "sayac.json"))
    monkeypatch.setenv("GUNLUK_ISTEK_LIMITI", "5")
    from src import sayac, main
    importlib.reload(sayac)
    importlib.reload(main)
    from fastapi.testclient import TestClient
    return TestClient(main.app), main


def test_ozellik_bayragi_kapaliyken_503(monkeypatch, tmp_path):
    istemci, _ = _istemci(monkeypatch, tmp_path, aktif="false")
    yanit = istemci.get("/uyari/NVDA")
    assert yanit.status_code == 503


def test_saglik_ucu_calisir(monkeypatch, tmp_path):
    istemci, _ = _istemci(monkeypatch, tmp_path, aktif="false")
    yanit = istemci.get("/saglik")
    assert yanit.status_code == 200
    assert yanit.json()["aktif"] is False


def test_gecersiz_sembol_400(monkeypatch, tmp_path):
    istemci, _ = _istemci(monkeypatch, tmp_path, aktif="true")
    yanit = istemci.get("/uyari/AB%20CD!")
    assert yanit.status_code == 400


def test_vane_hatasinda_502_sessizce_gecmez(monkeypatch, tmp_path):
    istemci, main = _istemci(monkeypatch, tmp_path, aktif="true")

    def sahte_hata(sembol):
        raise main.vane_istemci.VaneHatasi("baglanti koptu")

    monkeypatch.setattr(main.vane_istemci, "tara", sahte_hata)
    yanit = istemci.get("/uyari/NVDA")
    assert yanit.status_code == 502
    assert "basarisiz" in yanit.json()["detail"].lower()


def test_tavsiye_iceren_vane_yaniti_filtrelenir(monkeypatch, tmp_path):
    istemci, main = _istemci(monkeypatch, tmp_path, aktif="true")

    def sahte_basarili(sembol):
        return {
            "mesaj": "Bu hisse olumlu sinyaller vermektedir, alim firsati.",
            "kaynaklar": [],
            "sure_sn": 1.2,
        }

    monkeypatch.setattr(main.vane_istemci, "tara", sahte_basarili)
    yanit = istemci.get("/uyari/NVDA")
    assert yanit.status_code == 200
    gövde = yanit.json()
    assert gövde["filtre_tetiklendi"] is True
    assert "olumlu sinyaller" not in gövde["mesaj"].lower()


def test_gunluk_limit_asilinca_429(monkeypatch, tmp_path):
    istemci, main = _istemci(monkeypatch, tmp_path, aktif="true")
    monkeypatch.setattr(
        main.vane_istemci,
        "tara",
        lambda sembol: {"mesaj": "onemli bir gelisme bulunamadi.", "kaynaklar": [], "sure_sn": 0.5},
    )
    for _ in range(5):
        assert istemci.get("/uyari/AAPL").status_code == 200
    yanit = istemci.get("/uyari/AAPL")
    assert yanit.status_code == 429


def test_karar_uret_import_edilmiyor():
    """Y4: bu servis God Mode'un 3 kutsal main.py dosyasindan hicbirini
    import etmez - statik kaynak taramasiyla dogrulanir."""
    kok = os.path.join(os.path.dirname(__file__), "..", "src")
    for dosya in os.listdir(kok):
        if not dosya.endswith(".py"):
            continue
        with open(os.path.join(kok, dosya)) as f:
            satirlar = [s.strip() for s in f.readlines()]
        ithal_satirlari = [s for s in satirlar if s.startswith("import ") or s.startswith("from ")]
        for satir in ithal_satirlari:
            assert "karar_uret" not in satir
            assert "godmode-paper-trading" not in satir
