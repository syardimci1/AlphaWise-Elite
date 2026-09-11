"""Korunan dosya testleri — CLAUDE.md ve gorev kurali R1.

Bu dosyalar backtest hizalama calismasinin KAPSAMI DISINDADIR ve tek
satiri degismemelidir. Test bunu iki bagimsiz yoldan dogrular:

  1. Icerik kilidi (sha256) — `araclar/korunan_dosya_kilidi.json`
  2. git ile HEAD karsilastirmasi — main.py'ler icin

Koydugum kilit, cascade.py ve llmquant_client.py'nin koruma kuralindan
ONCEKI (18.08.2026 tarihli, commit edilmemis) degisikliklerini
gizlemez; onlari o haliyle dondurur ve durumu kayda gecirir.

Calistirma:  python3 -m pytest araclar/test_korunan_dosyalar.py -v
"""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
KILIT_YOLU = KOK / "araclar" / "korunan_dosya_kilidi.json"


def _kilit():
    assert KILIT_YOLU.exists(), (
        "korunan_dosya_kilidi.json yok — once "
        "`python3 araclar/korunan_dosya_kilidi.py` calistir")
    return json.loads(KILIT_YOLU.read_text(encoding="utf-8"))["dosyalar"]


def _dogrula(yol: str):
    kilit = _kilit()
    assert yol in kilit, f"{yol} kilitte yok"
    p = KOK / yol
    assert p.exists(), f"KORUNAN DOSYA SILINMIS: {yol}"
    simdi = hashlib.sha256(p.read_bytes()).hexdigest()
    assert simdi == kilit[yol]["sha256"], (
        f"KORUNAN DOSYA DEGISTIRILMIS: {yol}\n"
        f"  kilit: {kilit[yol]['sha256']}\n"
        f"  simdi: {simdi}")
    assert p.stat().st_size == kilit[yol]["bayt"]


def test_maa_main_protected():
    """maa/src/main.py — karar kodlari (EKLE/TUT/BEKLE/DIKKAT ET) burada."""
    _dogrula("maa/src/main.py")


def test_taa_main_protected():
    """taa/src/main.py — korunan dosyalar listesi CLAUDE.md'dekinden genistir."""
    _dogrula("taa/src/main.py")


def test_cascade_protected():
    _dogrula("maa/src/cascade.py")


def test_llmquant_client_protected():
    _dogrula("maa/src/llmquant_client.py")


@pytest.mark.parametrize("yol", ["maa/src/main.py", "taa/src/main.py"])
def test_main_dosyalari_HEAD_ile_ayni(yol):
    """Bagimsiz ikinci kanit: bu ikisi commit edilmis surumle de birebir ayni.

    (cascade.py ve llmquant_client.py bu testin DISINDA; onlar kilit
    konmadan once zaten HEAD'den farkliydi — bkz. modul basligi.)"""
    s = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", yol], cwd=KOK)
    assert s.returncode == 0, (
        f"{yol} HEAD'den farkli:\n"
        + subprocess.run(["git", "diff", "HEAD", "--", yol], cwd=KOK,
                         capture_output=True, text=True).stdout[:2000])


def test_kilit_durumu_DURUSTCE_kayitli():
    """Kilit, kilit anindaki HEAD durumunu dogru kaydetmis olmali —
    'temiz' gorunsun diye gercek gizlenmemis olmali."""
    kilit = _kilit()
    assert kilit["maa/src/main.py"]["kilit_aninda_HEAD_ile_ayni"] is True
    assert kilit["taa/src/main.py"]["kilit_aninda_HEAD_ile_ayni"] is True
    assert kilit["maa/src/cascade.py"]["kilit_aninda_HEAD_ile_ayni"] is False, (
        "cascade.py kilit aninda HEAD'den FARKLIYDI; kilit bunu kaydetmeli")
    assert kilit["maa/src/llmquant_client.py"]["kilit_aninda_HEAD_ile_ayni"] is False


def test_KILIT_KARSILASTIRMASI_anlamli_mi():
    """Tautoloji savunmasi: tek bayt degisince ozet degismeli."""
    veri = (KOK / "maa/src/main.py").read_bytes()
    a = hashlib.sha256(veri).hexdigest()
    b = hashlib.sha256(veri + b"\n").hexdigest()
    assert a != b, "ozet fonksiyonu degisiklige duyarsiz - test hicbir sey kanitlamaz"


def test_KILIT_MEKANIZMASI_degisikligi_yakaliyor(tmp_path, monkeypatch):
    """Mekanizma sinamasi: kilit, degistirilmis bir dosyayi GERCEKTEN yakalar mi?

    Korunan dosyalara dokunmadan sinamak icin gecici bir kopya agaci
    kurulur. Yakalamayan bir kilit her koside yesil yanar ve hicbir sey
    korumaz."""
    import araclar.test_korunan_dosyalar as modul

    (tmp_path / "maa" / "src").mkdir(parents=True)
    sahte = tmp_path / "maa" / "src" / "main.py"
    sahte.write_bytes(b"orijinal icerik\n")
    (tmp_path / "araclar").mkdir()
    kilit = tmp_path / "araclar" / "korunan_dosya_kilidi.json"
    kilit.write_text(json.dumps({"dosyalar": {"maa/src/main.py": {
        "sha256": hashlib.sha256(sahte.read_bytes()).hexdigest(),
        "bayt": sahte.stat().st_size,
        "kilit_aninda_HEAD_ile_ayni": True}}}), encoding="utf-8")

    monkeypatch.setattr(modul, "KOK", tmp_path)
    monkeypatch.setattr(modul, "KILIT_YOLU", kilit)

    modul._dogrula("maa/src/main.py")                 # degismemisken gecmeli

    sahte.write_bytes(b"orijinal icerik\n# tek satir eklendi\n")
    with pytest.raises(AssertionError, match="DEGISTIRILMIS"):
        modul._dogrula("maa/src/main.py")             # degisince KIRILMALI

    sahte.unlink()
    with pytest.raises(AssertionError, match="SILINMIS"):
        modul._dogrula("maa/src/main.py")             # silinince de KIRILMALI
