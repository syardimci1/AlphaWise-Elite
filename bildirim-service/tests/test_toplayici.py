"""Bildirim merkezi toplayicisi regresyon agi (Madde 28)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
import pytest
from src.toplayici import (zaman_coz, duzey_belirle, koseli_log_coz, jsonl_coz,
                           kaynak_oku, sirala, ozet, KRITIK, ALARM, UYARI, BILGI)


# ---------------------------------------------------------------- zaman cozme
def test_uc_tarih_bicimi_de_cozulur():
    assert zaman_coz("2026-09-03 03:45:37+0200") == "2026-09-03T03:45:37"
    assert zaman_coz("2026-09-06 01:35:01") == "2026-09-06T01:35:01"
    assert zaman_coz("Sun Aug 16 21:33:20 CEST 2026") == "2026-08-16T21:33:20"


def test_cozulemeyen_tarih_UYDURULMAZ():
    assert zaman_coz("dun aksam") is None
    assert zaman_coz("") is None


def test_tek_haneli_gun_dogru_doldurulur():
    assert zaman_coz("Wed Sep  3 07:05:09 CEST 2026") == "2026-09-03T07:05:09"


# -------------------------------------------------------------------- duzeyler
def test_kritik_alarm_alarmdan_AYRILIR():
    assert duzey_belirle("KRITIK ALARM: claude YOK") == KRITIK
    assert duzey_belirle("ALARM: claude CALISMIYOR") == ALARM
    assert duzey_belirle("UYARI: komut gonderildi ama...") == UYARI
    assert duzey_belirle("OK: claude calisiyor") == BILGI


# ------------------------------------------------------------- duz metin log
BEKCI_LOG = """\
[2026-09-06 01:30:01] [ana:claude1] OK: claude calisiyor
[2026-09-06 01:35:01] [ana:claude1] ALARM: claude CALISMIYOR (pane_pid=123)
[2026-09-06 01:40:01] [ana:claude1] KRITIK ALARM: yeniden baslatma TUTMADI
bu satir bicime uymuyor
"""


def test_koseli_log_yalnizca_alarmlari_alir():
    o = koseli_log_coz(BEKCI_LOG, "otonom_bekci")
    assert len(o) == 2
    assert {x["duzey"] for x in o} == {ALARM, KRITIK}


def test_koseli_log_bilgi_satirlari_da_istenebilir():
    o = koseli_log_coz(BEKCI_LOG, "otonom_bekci", yalnizca_alarm=False)
    assert len(o) == 3, "OK satiri da gelmeliydi"


def test_bicime_uymayan_satir_sessizce_ATLANIR_ama_digerleri_KALIR():
    o = koseli_log_coz(BEKCI_LOG, "x", yalnizca_alarm=False)
    assert all(x["zaman"] for x in o)


# -------------------------------------------------------------------- JSONL
JSONL = "\n".join([
    json.dumps({"olay": "uyarici", "saglikli": True, "oneri_sayisi": 0,
                "zaman": "2026-09-04T10:21:21+00:00"}),
    json.dumps({"olay": "bekci", "saglikli": False, "yeniden_baslatildi": True,
                "cikti": "godmode-paper-trading", "ardisik_basarisiz": 1,
                "zaman": "2026-09-04T10:21:43+00:00"}),
    json.dumps({"olay": "bekci", "saglikli": False, "ardisik_basarisiz": 4,
                "zaman": "2026-09-04T10:30:00+00:00"}),
    json.dumps({"olay": "uyarici", "saglikli": True, "oneri_sayisi": 3,
                "zaman": "2026-09-04T11:00:00+00:00"}),
    "bu json degil",
])


def test_jsonl_saglikli_false_alarm_uretir():
    o = jsonl_coz(JSONL, "oz_iyilestirme")
    duzeyler = [x["duzey"] for x in o]
    assert ALARM in duzeyler and KRITIK in duzeyler and UYARI in duzeyler
    assert BILGI not in duzeyler, "saglikli+onerisiz kayit alarm degildir"


def test_ardisik_basarisiz_esigi_KRITIGE_yukseltir():
    o = jsonl_coz(JSONL, "x")
    kritikler = [x for x in o if x["duzey"] == KRITIK]
    assert len(kritikler) == 1
    assert "olay=bekci" in kritikler[0]["mesaj"]


def test_bozuk_jsonl_satiri_digerlerini_DUSURMEZ():
    o = jsonl_coz(JSONL, "x")
    assert len(o) == 3


# ------------------------------------------ EN KRITIK: bakamadim != alarm yok
def test_olmayan_dosya_KAYNAK_YOK_der_bos_liste_DEMEZ(tmp_path):
    s = kaynak_oku(tmp_path / "yok.log", "test", "metin")
    assert s["durum"] == "kaynak_yok"
    assert s["olaylar"] == []
    assert "bulunamadı" in s["gerekce"]


def test_okunamayan_kaynak_ACIKCA_bildirilir(tmp_path):
    """MUTASYON BOSLUGU: ilk surum dosya izinlerini kapatarak okuma hatasi
    uretmeye calisiyordu; kod root olarak kostugu icin izin kontrolu ISLEMIYOR
    ve test SESSIZCE ATLANIYORDU. Atlanan bir test hicbir seyi korumaz —
    nitekim 'okunamadi' mesajini bozan mutasyon hayatta kalmisti.

    Dizin, VAR OLAN ama okunamayan bir yoldur ve her ortamda ayni sekilde
    OSError uretir; testin atlanmasina gerek kalmaz."""
    dizin = tmp_path / "bir_dizin"
    dizin.mkdir()
    s = kaynak_oku(dizin, "test", "metin")
    assert s["durum"] == "okunamadi", "dizin okunamayan kaynak sayilmali"
    assert s["olaylar"] == []
    assert "ALARM OLMADIĞI ANLAMINA GELMEZ" in s["gerekce"], (
        "okunamayan kaynak, kullaniciya alarm yokmus gibi gorunemez")


def test_okunamayan_kaynak_ozeti_de_kirletir(tmp_path):
    dizin = tmp_path / "d2"; dizin.mkdir()
    o = ozet([kaynak_oku(dizin, "test", "metin")])
    assert o["okunamayan_kaynak"] == 1
    assert o["guvenilir_sessizlik"] is False


def test_ozet_okunamayan_kaynak_varken_SESSIZLIGI_GUVENILIR_SAYMAZ():
    """En tehlikeli sessiz hata: kaynak okunamadigi icin bos donen liste,
    kullaniciya 'her sey yolunda' diye gorunur."""
    sonuclar = [
        {"kaynak": "a", "durum": "okundu", "olaylar": []},
        {"kaynak": "b", "durum": "okunamadi", "olaylar": []},
    ]
    o = ozet(sonuclar)
    assert o["toplam_olay"] == 0
    assert o["guvenilir_sessizlik"] is False
    assert "GELMEZ" in o["uyari_metni"]


def test_ozet_tum_kaynaklar_okunduysa_sessizlik_GUVENILIRDIR():
    sonuclar = [{"kaynak": "a", "durum": "okundu", "olaylar": []},
                {"kaynak": "b", "durum": "okundu", "olaylar": []}]
    o = ozet(sonuclar)
    assert o["guvenilir_sessizlik"] is True
    assert o["uyari_metni"] == ""


def test_ozet_duzeyleri_dogru_sayar():
    sonuclar = [{"kaynak": "a", "durum": "okundu", "olaylar": [
        {"duzey": KRITIK}, {"duzey": ALARM}, {"duzey": ALARM}, {"duzey": UYARI}]}]
    o = ozet(sonuclar)
    assert o["duzey_sayimi"][KRITIK] == 1
    assert o["duzey_sayimi"][ALARM] == 2
    assert o["duzey_sayimi"][UYARI] == 1
    # Olay VARKEN "sessizlik guvenilir mi" sorusu gecersizdir -> None.
    assert o["sessiz_mi"] is False
    assert o["guvenilir_sessizlik"] is None


# ------------------------------------------------------------------ siralama
def test_siralama_once_siddet_sonra_EN_YENI():
    olaylar = [
        {"duzey": ALARM, "zaman": "2026-09-01T10:00:00"},
        {"duzey": KRITIK, "zaman": "2026-08-01T10:00:00"},
        {"duzey": ALARM, "zaman": "2026-09-05T10:00:00"},
    ]
    s = sirala(olaylar)
    assert s[0]["duzey"] == KRITIK, "kritik once gelmeli"
    assert s[1]["zaman"] == "2026-09-05T10:00:00", "ayni duzeyde EN YENI once"


def test_zamani_cozulemeyen_olay_ATILMAZ_sona_konur():
    olaylar = [{"duzey": ALARM, "zaman": None},
               {"duzey": ALARM, "zaman": "2026-09-01T10:00:00"}]
    s = sirala(olaylar)
    assert len(s) == 2, "zamansiz olay ATILMAMALI - sessizce alarm yok etmek olur"
    assert s[-1]["zaman"] is None


def test_guvenilir_sessizlik_olay_VARKEN_gecersizdir_None_doner():
    """Ilk surum olay varken de False donuyordu ve cikti 'SESSIZLIK GUVENILIR
    MI: False' diye okunup sanki bir sorun varmis izlenimi veriyordu. Alan
    yalnizca liste BOSKEN anlamlidir."""
    o = ozet([{"kaynak": "a", "durum": "okundu",
               "olaylar": [{"duzey": ALARM}]}])
    assert o["sessiz_mi"] is False
    assert o["guvenilir_sessizlik"] is None


def test_bos_ve_temiz_ise_True_bos_ve_kirli_ise_False():
    temiz = ozet([{"kaynak": "a", "durum": "okundu", "olaylar": []}])
    assert temiz["sessiz_mi"] is True and temiz["guvenilir_sessizlik"] is True
    kirli = ozet([{"kaynak": "a", "durum": "okundu", "olaylar": []},
                  {"kaynak": "b", "durum": "okunamadi", "olaylar": []}])
    assert kirli["sessiz_mi"] is True and kirli["guvenilir_sessizlik"] is False
