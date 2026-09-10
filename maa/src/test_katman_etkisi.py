"""Katman ablasyonu testleri — madde 42.

En kritik sozlesme: bir katmani cikarmanin karari degistirmesinin IKI
ayri nedeni olabilir (esik kaymasi / yeter sayinin dusmesi) ve bunlari
tek sayida toplamak yaniltici olur.
"""
import pytest

from katman_etkisi import tek_kayit_ablasyon, toplu_ablasyon


def _k(id_, skorlar, karar="TUT"):
    return {"id": id_, "ticker": "X", "decision": karar,
            "total_score": None, "layer_scores": skorlar}


def _tam(**kv):
    """Bes katmani da tasiyan skor sozlugu."""
    taban = {"taa": 0, "faa": 0, "raa": 0, "saa": 0, "chronos": 0}
    taban.update(kv)
    return taban


# ------------------------------------------------------ tek kayit
def test_belirleyici_katman_esik_kaymasi_uretir():
    """faa=5 cikinca toplam 5 -> 0 duser; EKLE -> TUT."""
    t = tek_kayit_ablasyon(_k(1, _tam(faa=5)))
    assert t["taban_karar"] == "EKLE"
    d = t["katmanlar"]["faa"]
    assert d["degisti"] is True and d["esik_kaymasi"] is True
    assert d["yeter_sayi_dustu"] is False
    assert d["ablasyon_karar"] == "TUT"


def test_belirleyici_olmayan_katman_degisim_uretmez():
    """chronos=0 cikinca toplam degismez, karar ayni kalir."""
    t = tek_kayit_ablasyon(_k(1, _tam(faa=5)))
    d = t["katmanlar"]["chronos"]
    assert d["degisti"] is False and d["esik_kaymasi"] is False


def test_yeter_sayi_dususu_esik_kaymasindan_AYRILIR():
    """Uc katmanli kayitta herhangi birini cikarmak BEKLE uretir; bu,
    katmanin bilgi degeri hakkinda bir sey SOYLEMEZ."""
    t = tek_kayit_ablasyon(_k(1, {"taa": 1, "faa": 1, "raa": 1,
                                  "saa": None, "chronos": None}))
    d = t["katmanlar"]["taa"]
    assert d["ablasyon_karar"] == "BEKLE"
    assert d["degisti"] is True
    assert d["yeter_sayi_dustu"] is True
    assert d["esik_kaymasi"] is False, (
        "yeter sayi dususu esik kaymasi olarak sayilmis")


def test_olculemeyen_katman_isaretlenir():
    t = tek_kayit_ablasyon(_k(1, {"taa": 1, "faa": 1, "raa": 1,
                                  "saa": None, "chronos": None}))
    assert t["katmanlar"]["saa"]["olculdu"] is False
    assert t["katmanlar"]["taa"]["olculdu"] is True


def test_olculemeyen_katmani_cikarmak_degisim_URETMEZ():
    """None katman zaten toplama girmiyordu."""
    t = tek_kayit_ablasyon(_k(1, {"taa": 2, "faa": 2, "raa": 2,
                                  "saa": None, "chronos": None}))
    assert t["katmanlar"]["saa"]["degisti"] is False


def test_eski_dort_katmanli_sema_calisir():
    t = tek_kayit_ablasyon(_k(1, {"taa": 1, "faa": 4, "raa": 0, "saa": 0}))
    assert t is not None
    assert "chronos" not in t["katmanlar"], "kayitta olmayan katman raporlanmis"
    assert t["katmanlar"]["faa"]["esik_kaymasi"] is True


def test_replay_edilemeyen_kayit_None_doner():
    assert tek_kayit_ablasyon(_k(1, {"all_checks_clear": True})) is None
    assert tek_kayit_ablasyon(_k(1, {})) is None


def test_dikkat_et_dalinda_da_calisir():
    t = tek_kayit_ablasyon(_k(1, _tam(faa=-5)))
    assert t["taban_karar"] == "DIKKAT ET"
    assert t["katmanlar"]["faa"]["ablasyon_karar"] == "TUT"


# --------------------------------------------------------- toplu
def test_oran_yalnizca_OLCULDUGU_kayitlar_uzerinden():
    """Katmanin None oldugu kayitlari paydaya koymak, onu yapay olarak
    'etkisiz' gosterirdi - oysa orada zaten yoktu."""
    kayitlar = [
        _k(1, _tam(saa=5)),                                  # saa olculdu, belirleyici
        _k(2, {"taa": 1, "faa": 1, "raa": 1, "saa": None, "chronos": 1}),
        _k(3, {"taa": 1, "faa": 1, "raa": 1, "saa": None, "chronos": 1}),
    ]
    o = toplu_ablasyon(kayitlar)
    saa = o["katman_ozeti"]["saa"]
    assert saa["olculdugu_kayit"] == 1
    assert saa["esik_kaymasi"] == 1
    assert saa["esik_kaymasi_orani"] == 100.0, (
        "payda tum kayitlar alinmis olabilir")


def test_hic_olculmeyen_katmanda_oran_None():
    """Sifir degil None: 'hic olculmedi' ile 'etkisiz' ayni sey degil."""
    kayitlar = [_k(1, {"taa": 1, "faa": 1, "raa": 1, "saa": None,
                       "chronos": None})]
    o = toplu_ablasyon(kayitlar)
    assert o["katman_ozeti"]["chronos"]["esik_kaymasi_orani"] is None


def test_toplam_degisim_iki_turu_de_sayar():
    kayitlar = [_k(1, {"taa": 1, "faa": 1, "raa": 1, "saa": None,
                       "chronos": None})]
    o = toplu_ablasyon(kayitlar)["katman_ozeti"]["taa"]
    assert o["toplam_degisim"] == 1 and o["yeter_sayi_dustu"] == 1
    assert o["esik_kaymasi"] == 0


def test_replay_edilemeyenler_paydaya_girmez():
    kayitlar = [_k(1, _tam(faa=5)), _k(2, {"all_checks_clear": True}),
                _k(3, {"market_regime": "risk_on"})]
    assert toplu_ablasyon(kayitlar)["degerlendirilen_kayit"] == 1


def test_bos_girdi():
    o = toplu_ablasyon([])
    assert o["degerlendirilen_kayit"] == 0
    assert all(d["esik_kaymasi_orani"] is None
               for d in o["katman_ozeti"].values())


def test_gercek_veri_beklentisi():
    """Uretim olcumu (10.09.2026): faa acik ara en belirleyici katman.

    Burada o GERCEK degil, olcumun YONU kilitlenir: buyuk ve neredeyse
    sabit bir faa katkisi, ablasyonda yuksek esik kaymasi uretmeli.
    """
    kayitlar = [_k(i, _tam(faa=4, taa=0, raa=0, saa=0, chronos=0))
                for i in range(20)]
    o = toplu_ablasyon(kayitlar)["katman_ozeti"]
    assert o["faa"]["esik_kaymasi_orani"] == 100.0
    assert o["chronos"]["esik_kaymasi_orani"] == 0.0
