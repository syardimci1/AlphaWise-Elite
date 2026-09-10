"""Uretimdeki gibi PAKET olarak import testi.

NEDEN VAR
=========
10.09.2026'da taa restart dongusune girdi: walkforward.py "import
olcut_katmani" yaziyordu ve bu, cwd'nin /app/src oldugu TESTLERDE
calisiyordu — ama uretimde modul "src.walkforward" olarak yukleniyor
(uvicorn "src.main:app", main.py "from . import walkforward") ve duz
import ModuleNotFoundError veriyordu.

Yani mevcut testlerin tamami yesildi ve servis yine de acilmadi. Testin
calistigi bicim ile uretimin calistigi bicim farkliydi; bu testin isi tam
olarak o farki kapatmaktir.
"""
import importlib
import sys
from pathlib import Path

import pytest

DEPO_ICI = Path(__file__).resolve().parents[1]      # /app  (taa kokü)


@pytest.fixture
def paket_yolu():
    """Uretim ortamini SADIK bicimde kurar.

    Yalnizca /app'i sys.path'e eklemek YETMEZ: pytest calisma dizinini
    (/app/src) de sys.path'e koyar ve o zaman duz "import olcut_katmani"
    yine cozulur — yani test, uretimde kirilan kodu YESIL gosterirdi.
    Ilk yazimda tam olarak bu oldu. Bu yuzden src dizini sys.path'ten
    GECICI OLARAK CIKARILIR; boylece modullerin birbirini yalnizca paket
    yoluyla bulabildigi gercek durum sinanir.
    """
    src = str(DEPO_ICI / "src")
    kok = str(DEPO_ICI)
    onceki_yol = list(sys.path)
    sys.path[:] = [y for y in sys.path
                   if Path(y or ".").resolve() != Path(src).resolve()]
    if kok not in sys.path:
        sys.path.insert(0, kok)
    gizlenen = {ad: sys.modules.pop(ad)
                for ad in ("walkforward", "olcut_katmani") if ad in sys.modules}
    try:
        yield
    finally:
        sys.modules.update(gizlenen)
        sys.path[:] = onceki_yol


def test_walkforward_paket_olarak_import_edilebilir(paket_yolu):
    """Uretimin yaptigi sey: src.walkforward."""
    m = importlib.import_module("src.walkforward")
    assert hasattr(m, "olcumler")
    assert hasattr(m, "walk_forward")


def test_olcut_katmani_paket_yolundan_erisilebilir(paket_yolu):
    m = importlib.import_module("src.walkforward")
    assert hasattr(m, "_ok"), "olcut katmani baglanmamis"
    assert hasattr(m._ok, "calistir")


def test_paket_yolunda_olcumler_calisir(paket_yolu):
    """Import edilebilmek yetmez; olcut katmani gercekten donmeli."""
    import pandas as pd
    m = importlib.import_module("src.walkforward")
    sonuc = m.olcumler(pd.Series([0.01, -0.005, 0.02]), 3, 66.7)
    assert sonuc is not None
    assert sonuc["gun_sayisi"] == 3
    assert "sortino" in sonuc, "yeni olcutler paket yolunda gorunmuyor"


def test_hicbir_modul_ciplak_kardes_import_kullanmiyor():
    """Tum src/ dizinini tarayan YAPISAL denetim.

    Bir modul kardesini "import kardes" diye cagirirsa, testlerde (cwd
    /app/src) calisir ama uretimde paket olarak yuklendiginde
    ModuleNotFoundError verir. Tek bir dosyayi duzeltmek yetmez; bu test
    ayni hatanin BASKA bir dosyada tekrarlanmasini engeller.

    Not: src/__init__.py yok ve GEREKMIYOR — Python 3 ad alani paketleri
    sayesinde "src.walkforward" yine de yukleniyor (calisan servisle
    dogrulandi). Bu yuzden burada __init__.py aranmaz; asil risk olan
    ciklak kardes import'u aranir.
    """
    import re
    src = DEPO_ICI / "src"
    kardesler = {y.stem for y in src.glob("*.py")
                 if not y.name.startswith("test_") and y.stem != "__init__"}
    desen = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)",
                       re.M)
    ihlaller = []
    for dosya in sorted(src.glob("*.py")):
        if dosya.name.startswith("test_"):
            continue
        metin = dosya.read_text(encoding="utf-8")
        for satir_no, satir in enumerate(metin.splitlines(), 1):
            e = desen.match(satir)
            if not e:
                continue
            ad = e.group(1)
            if ad in kardesler and ad != dosya.stem:
                # try/except ile korunan geri donus yolu kabul edilir
                onceki = "\n".join(metin.splitlines()[max(0, satir_no - 4):satir_no])
                if "except ImportError" in onceki or "try:" in onceki:
                    continue
                ihlaller.append(f"{dosya.name}:{satir_no}: {satir.strip()}")
    assert not ihlaller, (
        "ciplak kardes import bulundu; uretimde paket yuklemesinde kirilir:\n"
        + "\n".join(ihlaller))
