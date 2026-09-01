"""
SAA YANIT SOZLESMESI REGRESYON TESTLERI (02.09.2026).

=====================================================================
NEDEN VAR
=====================================================================
saa/src/main.py'ye "olculemedi != gercek notr" ayrimi eklendi: ariza
yollari artik top-level "error" anahtari, average_score=None ve
overall="veri_yok" donduruyor.

Bu ayrim TAMAMEN bir SOZLESMEYE dayaniyor ve sozlesmenin karsi tarafi
KORUNAN bir dosyada (maa/src/main.py:506-514):

    def score_saa(data):
        if not data or "error" in data:
            return None          # <- katman YOK sayilir (dogru)
        ...
        return 0                 # <- katman VAR, notr oyu (yanlis olurdu)

Yani "error" anahtarinin adi degisir ya da _olculemedi() geri alinirsa,
sistem SESSIZCE eski hataya doner: olculmemis bir notr, olculmus gibi
karar skoruna girer ve MAA'nin "Confluence over Confidence" kapisi
(layers_available >= 3) sahte bir katmanla gecilebilir.

Denetimde olculdu: bu sozlesmeyi dogrulayan TEK BIR TEST YOKTU. Bu dosya
o boslugu kapatir. MAA korunan dosya oldugu icin oradaki mantik
degistirilemez - dolayisiyla koruma SAA tarafinda olmak ZORUNDA.

=====================================================================
NASIL KOSULUR
=====================================================================
    docker run --rm -v $PWD:/app -w /app <saa-imaji> \
        sh -c "pip install -q pytest && python3 -m pytest tests/ -q"

Ag erisimi GEREKMEZ: Finnhub ve FinBERT cagrilari yamalanir (monkeypatch).
Hicbir ucretli API cagrilmaz (BUTCE ONAY KURALI).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import main as saa  # noqa: E402


# --- yardimcilar ---------------------------------------------------------

def _haber(n=3):
    return {"news": [{"headline": f"Baslik {i}"} for i in range(n)]}


def _finbert_ok(etiket="neutral", skor=0.9, n=3):
    return {"results": [{"label": etiket, "score": skor, "text": f"Baslik {i}"}
                        for i in range(n)]}


ARIZA_ANAHTARLARI = ("error", "olculemedi")


def _ariza_mi(yanit: dict) -> bool:
    """Bir yanitin OLCULEMEDI sozlesmesine uydugunu dogrular."""
    return (
        "error" in yanit
        and yanit.get("olculemedi") is True
        and yanit.get("average_score") is None
        and yanit.get("overall") == "veri_yok"
    )


# =====================================================================
# 1) DORT ARIZA YOLUNUN DORDU DE "OLCULEMEDI" SOZLESMESINE UYAR
# =====================================================================

def test_haber_cekilemedi_olculemedi(monkeypatch):
    monkeypatch.setattr(saa, "fetch_finnhub_news",
                        lambda t, m: {"error": "Tum anahtarlar basarisiz"})
    y = saa.analyze_ticker("MSFT")
    assert _ariza_mi(y), y


def test_haber_yok_olculemedi(monkeypatch):
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: {"news": []})
    y = saa.analyze_ticker("MSFT")
    assert _ariza_mi(y), y


def test_baslik_yok_olculemedi(monkeypatch):
    # Haber var ama hicbirinin basligi yok
    monkeypatch.setattr(saa, "fetch_finnhub_news",
                        lambda t, m: {"news": [{"headline": ""}, {}]})
    y = saa.analyze_ticker("MSFT")
    assert _ariza_mi(y), y


def test_finbert_hatasi_olculemedi(monkeypatch):
    """ASIL BULUNAN HATA: FinBERT 503 -> eskiden overall='neutral' idi."""
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: _haber())
    monkeypatch.setattr(saa, "score_with_finbert",
                        lambda t: {"error": "FinBERT HTTP 503"})
    y = saa.analyze_ticker("MSFT")
    assert _ariza_mi(y), y
    assert "503" in y["error"]


# =====================================================================
# 2) BOZUK FINBERT GOVDESI DE OLCULEMEDI (HTTP 500 deligi)
# =====================================================================
# MAA'nin _fetch_one'i (korunan dosya) resp.status_code'u KONTROL ETMEZ;
# SAA 500 dondurse FastAPI govdesi {"detail": ...} olur ve o sozlukte
# "error" anahtari YOKTUR -> score_saa 0 doner -> SAHTE KATMAN.
# Bu yuzden SAA'nin HIC 500 DONDURMEMESI gerekir.

@pytest.mark.parametrize("bozuk", [
    {"results": []},                      # bos liste
    {"results": None},                    # liste degil
    {},                                   # results anahtari hic yok
    {"results": ["metin"]},               # eleman sozluk degil
    {"results": [{"label": "positive"}]},  # score alani eksik
    {"results": [{"score": 0.9}]},         # label alani eksik
])
def test_bozuk_finbert_govdesi_500_DEGIL_olculemedi(monkeypatch, bozuk):
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: _haber())
    monkeypatch.setattr(saa, "score_with_finbert", lambda t: bozuk)
    y = saa.analyze_ticker("MSFT")   # istisna FIRLATMAMALI
    assert _ariza_mi(y), y


# =====================================================================
# 3) BASARI YOLU BOZULMADI
# =====================================================================

def test_basari_yolunda_error_YOK(monkeypatch):
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: _haber())
    monkeypatch.setattr(saa, "score_with_finbert", lambda t: _finbert_ok("positive", 0.8))
    y = saa.analyze_ticker("MSFT")
    assert "error" not in y
    assert y.get("olculemedi") is not True
    assert isinstance(y["average_score"], (int, float))
    assert y["overall"] in ("positive", "negative", "neutral")
    assert y["data_status"] == "ok"


def test_gercek_notr_olculemediden_AYRI(monkeypatch):
    """ASIL AYRIM: gercekten notr cikan bir olcum, ariza gibi gorunmemeli."""
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: _haber())
    monkeypatch.setattr(saa, "score_with_finbert", lambda t: _finbert_ok("neutral", 0.9))
    gercek = saa.analyze_ticker("MSFT")

    monkeypatch.setattr(saa, "score_with_finbert", lambda t: {"error": "FinBERT HTTP 503"})
    ariza = saa.analyze_ticker("MSFT")

    assert gercek["overall"] == "neutral" and "error" not in gercek
    assert ariza["overall"] == "veri_yok" and "error" in ariza
    assert gercek["overall"] != ariza["overall"], "iki durum AYIRT EDILEBILIR olmali"


# =====================================================================
# 4) MAA SOZLESMESI - KRITIK BAGLANTI
# =====================================================================
# maa/src/main.py:506-514 KORUNAN dosyadir ve degistirilemez. Onun
# mantigi burada BIREBIR yeniden uretilir; SAA tarafi degisirse bu test
# kirilir ve sessiz gerileme onlenir.

def _score_saa_kopyasi(data):
    """maa/src/main.py:506-514'un birebir kopyasi (korunan dosya okunmadan
    degistirilemez; bu kopya sozlesmeyi test icinde sabitler)."""
    if not data or "error" in data:
        return None
    sentiment = data.get("overall")
    if sentiment == "positive":
        return 1
    elif sentiment == "negative":
        return -1
    return 0


def test_MAA_arizayi_KATMAN_YOK_sayar(monkeypatch):
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: _haber())
    monkeypatch.setattr(saa, "score_with_finbert", lambda t: {"error": "FinBERT HTTP 503"})
    ariza = saa.analyze_ticker("MSFT")
    assert _score_saa_kopyasi(ariza) is None, (
        "Ariza yaniti MAA'da None (katman yok) olmali; 0 olursa SAHTE KATMAN doner")


def test_MAA_gercek_notru_KATMAN_VAR_sayar(monkeypatch):
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: _haber())
    monkeypatch.setattr(saa, "score_with_finbert", lambda t: _finbert_ok("neutral", 0.9))
    gercek = saa.analyze_ticker("MSFT")
    assert _score_saa_kopyasi(gercek) == 0, "Gercek notr bir katman oyudur (0)"


def test_ONCESI_SONRASI_eski_sozlesme_ayirt_EDEMIYORDU():
    """Duzeltmeden onceki ciktiyi elle kurup farki belgeler."""
    eski_ariza = {"ticker": "MSFT", "news_count": 0, "average_score": 0.0,
                  "overall": "neutral", "data_status": "sentiment_atlandi: 503"}
    eski_gercek = {"ticker": "MSFT", "news_count": 3, "average_score": 0.0,
                   "overall": "neutral", "data_status": "ok"}
    assert _score_saa_kopyasi(eski_ariza) == _score_saa_kopyasi(eski_gercek) == 0, (
        "eski sozlesmede ikisi de 0 idi - ayirt edilemiyordu")


# =====================================================================
# 5) SIGNAL-LEDGER SOZLESMESI
# =====================================================================
# signal-ledger/src/main.py:112-123 average_score'u okur. Ariza yolunda
# None gelmeli ki sutuna SAHTE 0.0 yerine NULL yazilsin.

def test_signal_ledger_arizada_NULL_yazar(monkeypatch):
    monkeypatch.setattr(saa, "fetch_finnhub_news", lambda t, m: _haber())
    monkeypatch.setattr(saa, "score_with_finbert", lambda t: {"error": "FinBERT HTTP 503"})
    saa_raw = saa.analyze_ticker("MSFT")

    # signal-ledger'daki mantigin birebir kopyasi
    sentiment_score = None
    if isinstance(saa_raw, dict) and "average_score" in saa_raw:
        sentiment_score = saa_raw.get("average_score")
    layer_scores_saa = _score_saa_kopyasi(saa_raw)
    yazilacak = sentiment_score if sentiment_score is not None else layer_scores_saa

    assert yazilacak is None, "arizada sutuna NULL yazilmali, 0.0 DEGIL"
