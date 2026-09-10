"""Madde 34 — karar replay testleri.

En kritik test: test_kural_main_py_ile_ayni_mi. Replay modulu korunan
main.py'yi ITHAL EDEMEZ (FastAPI/LLM/veritabani yan etkileri). Bu yuzden
kural burada bagimsiz yazildi. Boyle bir kopya SESSIZCE ayrisabilir —
main.py'de esik degisir, replay eski esikle "sadik" rapor verir. Asagidaki
test main.py'nin KAYNAK METNINI okuyup esiklerin hala ayni oldugunu
dogrular; ayrismayi TEST kirilmasi olarak gorunur kilar.
"""
import json
import re
from pathlib import Path

import pytest

from karar_replay import (ASGARI_KATMAN, DIKKAT_ESIGI, EKLE_ESIGI, karar_uret,
                          kayit_replay, kural_kapsamasi, sema_sinifi,
                          toplu_replay)

MAIN_PY = Path(__file__).resolve().parent / "main.py"


# --------------------------------------------------------------- kural kilidi
def test_kural_main_py_ile_ayni_mi():
    """Korunan main.py'deki esikler replay modulundekiyle ayni olmali."""
    kaynak = MAIN_PY.read_text(encoding="utf-8")
    assert f"layers_available < {ASGARI_KATMAN}" in kaynak, (
        f"main.py'deki asgari katman esigi degismis olabilir; "
        f"karar_replay.ASGARI_KATMAN={ASGARI_KATMAN}")
    assert re.search(rf"total_score\s*<=\s*{DIKKAT_ESIGI}\b", kaynak), (
        f"main.py'deki DIKKAT ET esigi karar_replay.DIKKAT_ESIGI="
        f"{DIKKAT_ESIGI} ile uyusmuyor")
    assert re.search(rf"total_score\s*>=\s*{EKLE_ESIGI}\b", kaynak), (
        f"main.py'deki EKLE esigi karar_replay.EKLE_ESIGI={EKLE_ESIGI} "
        f"ile uyusmuyor")


def test_kural_karar_metinleri_main_py_ile_ayni():
    """Karar kodlari (EKLE/TUT/BEKLE/DIKKAT ET) main.py ile birebir ayni."""
    kaynak = MAIN_PY.read_text(encoding="utf-8")
    for kod in ("EKLE", "TUT", "BEKLE", "DIKKAT ET"):
        assert f'"{kod}"' in kaynak, f"main.py'de {kod} karar kodu bulunamadi"


# ------------------------------------------------------------- karar_uret
def test_uc_katmandan_az_bekle_ve_toplam_none():
    s = karar_uret({"taa": 5, "faa": 5, "raa": None, "saa": None, "chronos": None})
    assert s["karar"] == "BEKLE"
    assert s["toplam"] is None, "olculemedi durumunda toplam skor uretilmemeli"
    assert s["gecerli_katman"] == 2


def test_olculemedi_sifir_sayilmaz():
    """None katman toplama 0 olarak girmemeli — 232d1a0 degismezi."""
    a = karar_uret({"taa": 2, "faa": 2, "raa": 2, "saa": None, "chronos": None})
    b = karar_uret({"taa": 2, "faa": 2, "raa": 2, "saa": 0, "chronos": 0})
    assert a["gecerli_katman"] == 3 and b["gecerli_katman"] == 5
    assert a["toplam"] == b["toplam"] == 6      # toplam ayni
    # ama gecerli katman sayisi farkli: None sifir DEGIL, YOK
    c = karar_uret({"taa": 2, "faa": 2, "raa": None, "saa": None, "chronos": None})
    d = karar_uret({"taa": 2, "faa": 2, "raa": 0, "saa": 0, "chronos": 0})
    assert c["karar"] == "BEKLE" and d["karar"] == "EKLE", (
        "None'lari sifir saymak karari BEKLE'den EKLE'ye cevirirdi")


@pytest.mark.parametrize("toplam,beklenen", [
    (-10, "DIKKAT ET"), (-4, "DIKKAT ET"), (-3, "DIKKAT ET"),
    (-2, "TUT"), (0, "TUT"), (3, "TUT"),
    (4, "EKLE"), (5, "EKLE"), (12, "EKLE"),
])
def test_esik_sinirlari(toplam, beklenen):
    """Esik SINIRLARI tam noktasinda dogrulanir (-3 ve 4 dahil)."""
    skorlar = {"taa": toplam, "faa": 0, "raa": 0}
    assert karar_uret(skorlar)["karar"] == beklenen


def test_bos_girdi_bekle():
    assert karar_uret({})["karar"] == "BEKLE"
    assert karar_uret(None)["karar"] == "BEKLE"


# ------------------------------------------------------------- sema_sinifi
@pytest.mark.parametrize("ls,beklenen", [
    ({"taa": 1, "faa": 1, "raa": 1, "saa": 1, "chronos": 1}, "maa_5_katman"),
    ({"taa": 1, "faa": 1, "raa": 1, "saa": 1}, "maa_4_katman_eski"),
    ({"cash_position_pct": 5, "market_regime": "risk_on",
      "target_portfolio": [], "total_invested_pct": 95}, "portfoy_sinyali"),
    ({"all_checks_clear": True, "master_model": "x", "analyst_model": "y",
      "constitution_check": True, "critic_feedback": "", "critic_model": "z",
      "retry_count": 0}, "llm_kaskadi"),
    ({"all_checks_clear": True, "source": "godmode"}, "god_mode"),
    ({}, "katman_skoru_yok"),
    (None, "katman_skoru_yok"),
    ({"beklenmeyen": 1}, "bilinmeyen_sema"),
])
def test_sema_siniflari(ls, beklenen):
    assert sema_sinifi(ls) == beklenen


# ------------------------------------------------------------- kayit_replay
def test_kapsam_disi_kayit_basarisizlik_sayilmaz():
    s = kayit_replay({"id": 1, "ticker": "SPY", "decision": "bilinmiyor",
                      "total_score": None,
                      "layer_scores": {"all_checks_clear": True, "source": "g"}})
    assert s["durum"] == "replay_edilemez"
    assert s["uretilen_karar"] is None
    assert "BASARISIZLIK DEGIL" in s["gerekce"]


def test_gercek_kayit_uyar():
    """Canli decision_log satiri (id=217, WDC)."""
    s = kayit_replay({"id": 217, "ticker": "WDC", "decision": "EKLE",
                      "total_score": 6,
                      "layer_scores": {"faa": 5, "raa": 0, "saa": 0,
                                       "taa": 0, "chronos": 1}})
    assert s["durum"] == "uydu" and s["uretilen_karar"] == "EKLE"
    assert s["uretilen_toplam"] == 6


def test_null_katmanli_gercek_kayit_uyar():
    """id=216 CAT — saa null. Kayit None'i koruyor, replay de korumali."""
    s = kayit_replay({"id": 216, "ticker": "CAT", "decision": "TUT",
                      "total_score": 2,
                      "layer_scores": {"faa": 1, "raa": 1, "saa": None,
                                       "taa": 0, "chronos": 0}})
    assert s["durum"] == "uydu"
    assert s["gecerli_katman"] == 4, "null katman sayilmamali"


def test_uymayan_kayit_yakalanir():
    """Kayitli karar kuralla celisiyorsa replay bunu ORTMEMELI."""
    s = kayit_replay({"id": 9, "ticker": "XYZ", "decision": "EKLE",
                      "total_score": 1,
                      "layer_scores": {"faa": 1, "raa": 0, "saa": 0,
                                       "taa": 0, "chronos": 0}})
    assert s["durum"] == "uymadi"
    assert s["uretilen_karar"] == "TUT"
    assert "kayitli=EKLE" in s["gerekce"]


def test_toplam_uymazsa_karar_uysa_bile_uymadi():
    """Karar dogru ama toplam skor kayitla celisiyorsa yine de uymadi."""
    s = kayit_replay({"id": 10, "ticker": "XYZ", "decision": "TUT",
                      "total_score": 99,
                      "layer_scores": {"faa": 1, "raa": 0, "saa": 0,
                                       "taa": 0, "chronos": 0}})
    assert s["karar_uydu"] is True and s["toplam_uydu"] is False
    assert s["durum"] == "uymadi"


def test_bekle_kaydinda_toplam_none_beklenir():
    s = kayit_replay({"id": 11, "ticker": "XYZ", "decision": "BEKLE",
                      "total_score": None,
                      "layer_scores": {"faa": 1, "raa": None, "saa": None,
                                       "taa": None, "chronos": None}})
    assert s["durum"] == "uydu" and s["uretilen_toplam"] is None


def test_bekle_kaydinda_sifir_toplam_uymaz():
    """Kayitta BEKLE ama total_score=0 yazilmissa bu 'olculemedi=sifir'
    hatasidir ve replay bunu uyusmazlik olarak GORMELIDIR."""
    s = kayit_replay({"id": 12, "ticker": "XYZ", "decision": "BEKLE",
                      "total_score": 0,
                      "layer_scores": {"faa": 1, "raa": None, "saa": None,
                                       "taa": None, "chronos": None}})
    assert s["durum"] == "uymadi", "BEKLE + toplam=0 sessizce gecmemeli"


def test_metin_total_score_sayiya_cevrilir():
    """TimescaleDB numeric alani metin olarak gelebilir."""
    s = kayit_replay({"id": 13, "ticker": "XYZ", "decision": "EKLE",
                      "total_score": "6",
                      "layer_scores": {"faa": 5, "raa": 0, "saa": 0,
                                       "taa": 0, "chronos": 1}})
    assert s["durum"] == "uydu"


# ------------------------------------------------------------- toplu_replay
def test_ozet_kapsam_disini_paydaya_koymaz():
    kayitlar = [
        {"id": 1, "ticker": "A", "decision": "EKLE", "total_score": 6,
         "layer_scores": {"faa": 5, "raa": 0, "saa": 0, "taa": 0, "chronos": 1}},
        {"id": 2, "ticker": "B", "decision": "bilinmiyor", "total_score": None,
         "layer_scores": {"all_checks_clear": True, "source": "g"}},
        {"id": 3, "ticker": "C", "decision": "bilinmiyor", "total_score": None,
         "layer_scores": {"market_regime": "risk_on"}},
    ]
    o = toplu_replay(kayitlar)
    assert o["toplam_kayit"] == 3
    assert o["replay_edilebilir"] == 1
    assert o["kapsam_disi"] == 2
    assert o["sadakat_orani"] == 1.0, (
        "kapsam disi kayitlar orani dusurmemeli")
    assert o["sema_dagilimi"]["god_mode"] == 1


def test_ozet_uymayanlari_listeler():
    kayitlar = [
        {"id": 1, "ticker": "A", "decision": "EKLE", "total_score": 1,
         "layer_scores": {"faa": 1, "raa": 0, "saa": 0, "taa": 0, "chronos": 0}},
    ]
    o = toplu_replay(kayitlar)
    assert o["uymayan"] == 1 and o["sadakat_orani"] == 0.0
    assert len(o["uymayanlar"]) == 1 and o["uymayanlar"][0]["id"] == 1


def test_hicbir_replay_edilebilir_kayit_yoksa_oran_none():
    """Sifir kayitta oran 1.0 (kusursuz) DEGIL, None (olculemedi) olmali."""
    o = toplu_replay([{"id": 1, "ticker": "A", "decision": "x",
                       "total_score": None, "layer_scores": {}}])
    assert o["sadakat_orani"] is None, "olculemedi orani 1.0 gibi gosterilemez"
    assert o["replay_edilebilir"] == 0


def test_bos_liste():
    o = toplu_replay([])
    assert o["toplam_kayit"] == 0 and o["sadakat_orani"] is None


# --------------------------------------------------------- kural_kapsamasi
def _k(id_, karar, toplam, skorlar):
    return {"id": id_, "ticker": "X", "decision": karar,
            "total_score": toplam, "layer_scores": skorlar}


def test_kapsama_sinanmayan_dali_bildirir():
    """Veri yalnizca EKLE uretiyorsa oteki uc dal sinanmamis sayilmali."""
    kayitlar = [_k(1, "EKLE", 6, {"faa": 6, "raa": 0, "saa": 0,
                                  "taa": 0, "chronos": 0})]
    k = kural_kapsamasi(kayitlar)
    assert k["tam_kapsam"] is False
    assert set(k["sinanmayan_dallar"]) == {"TUT", "BEKLE", "DIKKAT ET"}
    assert "DIKKAT ET" in k["uyari"] and "BILGI VERMEZ" in k["uyari"]


def test_kapsama_tam_oldugunda_uyari_yok():
    kayitlar = [
        _k(1, "EKLE", 6, {"faa": 6, "raa": 0, "saa": 0, "taa": 0, "chronos": 0}),
        _k(2, "TUT", 1, {"faa": 1, "raa": 0, "saa": 0, "taa": 0, "chronos": 0}),
        _k(3, "BEKLE", None, {"faa": 1, "raa": None, "saa": None,
                              "taa": None, "chronos": None}),
        _k(4, "DIKKAT ET", -5, {"faa": -5, "raa": 0, "saa": 0,
                                "taa": 0, "chronos": 0}),
    ]
    k = kural_kapsamasi(kayitlar)
    assert k["tam_kapsam"] is True and k["uyari"] == ""
    assert k["dal_sayimi"] == {"EKLE": 1, "TUT": 1, "BEKLE": 1, "DIKKAT ET": 1}


def test_kapsama_kapsam_disi_kayitlari_saymaz():
    kayitlar = [
        _k(1, "EKLE", 6, {"faa": 6, "raa": 0, "saa": 0, "taa": 0, "chronos": 0}),
        _k(2, "bilinmiyor", None, {"all_checks_clear": True, "source": "g"}),
    ]
    assert sum(kural_kapsamasi(kayitlar)["dal_sayimi"].values()) == 1


def test_kapsama_uretim_verisi_gercegi():
    """09.2026 dokumunde uretim verisi DIKKAT ET dalini hic uretmemisti.

    Bu test o gercegi degil, RAPORLAMA davranisini kilitler: negatif skor
    tasimayan bir kumede DIKKAT ET sinanmamis olarak bildirilmelidir.
    """
    kayitlar = [_k(i, "TUT", 2, {"faa": 2, "raa": 0, "saa": 0,
                                 "taa": 0, "chronos": 0}) for i in range(10)]
    k = kural_kapsamasi(kayitlar)
    assert "DIKKAT ET" in k["sinanmayan_dallar"]
