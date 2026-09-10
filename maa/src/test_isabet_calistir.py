"""Isabet kosucusu testleri — madde 47 (saf kisimlar).

Veritabani dokunmayan fonksiyonlar test edilir: piyasa getirisi hesabi,
tatil gunu geri bakma, ve satir degerlendirmesi. Yazma yolu ayri olarak
canli olarak dogrulanmistir (kuru calisma + yazma).
"""
from datetime import date

import pytest

from isabet_calistir import (_en_yakin_kapanis, piyasa_getirisi,
                             satirlari_degerlendir)
from isabet_olcut import DOGRU, OLCULEMEDI, UYGULANAMAZ, YANLIS  # noqa: F401

SERI = {
    "2026-07-22": 100.0,
    "2026-07-23": 101.0,
    "2026-08-21": 109.0,
    "2026-08-22": 110.0,
}


# --------------------------------------------------- en yakin kapanis
def test_tam_gun_bulunur():
    k, g = _en_yakin_kapanis(SERI, date(2026, 7, 22))
    assert k == 100.0 and g == "2026-07-22"


def test_tatil_gununde_GERIYE_bakilir():
    """2026-08-23 seride yok; bir gun geriye (08-22) bakilmali."""
    k, g = _en_yakin_kapanis(SERI, date(2026, 8, 23))
    assert k == 110.0 and g == "2026-08-22"


def test_ILERI_bakilmaz():
    """Ileri bakmak, karar aninda bilinmeyen bir fiyati kullanmak olurdu."""
    k, g = _en_yakin_kapanis(SERI, date(2026, 7, 21))
    assert k is None, f"gelecege bakildi: {g}"


def test_cok_geriye_bakilmaz():
    k, _ = _en_yakin_kapanis(SERI, date(2026, 8, 15), geriye=3)
    assert k is None


# ------------------------------------------------------ piyasa getirisi
def test_piyasa_getirisi_hesaplanir():
    g, notu = piyasa_getirisi(SERI, date(2026, 7, 22), date(2026, 8, 22))
    assert g == pytest.approx(0.10)
    assert "2026-07-22" in notu and "2026-08-22" in notu


def test_piyasa_getirisi_okunamayinca_None():
    g, notu = piyasa_getirisi({}, date(2026, 7, 22), date(2026, 8, 22))
    assert g is None and "kapanis yok" in notu


def test_sifir_kapanis_bolme_yapmaz():
    g, notu = piyasa_getirisi({"2026-07-22": 0.0, "2026-08-22": 110.0},
                             date(2026, 7, 22), date(2026, 8, 22))
    assert g is None and "gecersiz" in notu


# --------------------------------------------------- satir degerlendirme
def _satir(id_, karar, getiri, gun=31):
    b = date(2026, 7, 22)
    return {"id": id_, "ticker": "X", "decision": karar, "pct_change": getiri,
            "decided_at": b, "evaluated_at": date.fromordinal(b.toordinal() + gun)}


def test_tut_piyasaya_gore_degerlendirilir():
    # piyasa %10, hisse %12 -> sapma %2 -> dogru
    s = satirlari_degerlendir([_satir(1, "TUT", 0.12)], SERI)[0]
    assert s["sonuc"] == DOGRU and s["piyasa"] == pytest.approx(0.10)


def test_tut_piyasadan_ayrisirsa_yanlis():
    s = satirlari_degerlendir([_satir(1, "TUT", 0.25)], SERI)[0]
    assert s["sonuc"] == YANLIS


def test_bekle_uygulanamaz():
    s = satirlari_degerlendir([_satir(1, "BEKLE", 0.12)], SERI)[0]
    assert s["sonuc"] == UYGULANAMAZ


def test_sifir_gunluk_pencere_olculemedi():
    """OLCULEN HATA: id=2 kaydi ayni gun degerlendirilmis ve dogru sayilmisti."""
    s = satirlari_degerlendir([_satir(2, "TUT", 0.0012, gun=0)], SERI)[0]
    assert s["sonuc"] == OLCULEMEDI and "en az" in s["gerekce"]


def test_piyasa_okunamazsa_TUT_olculemedi_ama_EKLE_olculur():
    satirlar = [_satir(1, "TUT", 0.05), _satir(2, "EKLE", 0.05)]
    sonuc = {s["id"]: s for s in satirlari_degerlendir(satirlar, {})}
    assert sonuc[1]["sonuc"] == OLCULEMEDI
    assert sonuc[2]["sonuc"] == DOGRU, "EKLE piyasa verisi gerektirmemeli"


def test_gerekce_piyasa_penceresini_bildirir():
    s = satirlari_degerlendir([_satir(1, "TUT", 0.12)], SERI)[0]
    assert "SPY" in s["gerekce"]


def test_bos_liste():
    assert satirlari_degerlendir([], SERI) == []


def test_id_korunur():
    ids = [s["id"] for s in satirlari_degerlendir(
        [_satir(7, "EKLE", 0.1), _satir(9, "TUT", 0.1)], SERI)]
    assert ids == [7, 9]


# ============================================================================
# 10.09.2026 — dusmanca dogrulama turunda bulunan kusurlar
# ============================================================================

def test_KISA_PENCERELI_BEKLE_uygulanamaz_kalir():
    """BULUNAN HATA: kontrol sirasi tersti; pencere once bakiliyordu ve kisa
    pencereli BEKLE 'olculemedi' oluyordu.

    Ayrim onemli: 'uygulanamaz' = daha uzun beklemek DE ise yaramaz;
    'olculemedi' = daha iyi veriyle olculebilirdi."""
    for gun in (0, 5, 19, 31):
        s = satirlari_degerlendir([_satir(1, "BEKLE", 0.05, gun=gun)], SERI)[0]
        assert s["sonuc"] == UYGULANAMAZ, (
            f"pencere {gun} gun -> {s['sonuc']} (uygulanamaz olmaliydi)")


def test_kisa_pencereli_ANAYASA_DISI_kod_da_uygulanamaz():
    for gun in (0, 31):
        s = satirlari_degerlendir([_satir(1, "BELIRSIZ", 0.05, gun=gun)], SERI)[0]
        assert s["sonuc"] == UYGULANAMAZ


def test_olculemedi_satirina_piyasa_getirisi_YAZILMAZ():
    """BULUNAN HATA: sifir gunluk pencerede hesap 0,0 veriyor ve bu
    'piyasa duzdu' diye okunuyordu - olculemedi'yi sifira cevirmek."""
    s = satirlari_degerlendir([_satir(2, "TUT", 0.0012, gun=0)], SERI)[0]
    assert s["sonuc"] == OLCULEMEDI
    assert s["piyasa"] is None, f"olculemedi satirina {s['piyasa']} yazildi"


def test_uygulanamaz_satirina_da_piyasa_YAZILMAZ():
    s = satirlari_degerlendir([_satir(1, "BEKLE", 0.05)], SERI)[0]
    assert s["piyasa"] is None


def test_piyasa_okunamayinca_NEDEN_gerekcede_kalir():
    """BULUNAN HATA: kosul terstIi; neden tam da gerektigi anda atiliyordu."""
    s = satirlari_degerlendir([_satir(1, "TUT", 0.05)], {})[0]
    assert s["sonuc"] == OLCULEMEDI
    assert "SPY" in s["gerekce"] or "kapanis yok" in s["gerekce"], (
        f"piyasa hatasinin nedeni gerekceden atilmis: {s['gerekce']}")


def test_decided_at_TUM_DALLARDA_tasinir():
    """Hypertable birincil anahtari (id, decided_at) - yazma icin gerekli.

    Ilk yazimda yalnizca 'olculdu' dali sinaniyordu; mutasyon
    'uygulanamaz' dalindan decided_at'i cikardiginda test gecmisti.
    Uc dal da kapsanmali."""
    dallar = [
        ("olculdu",     _satir(1, "EKLE", 0.05)),
        ("uygulanamaz", _satir(2, "BEKLE", 0.05)),
        ("olculemedi",  _satir(3, "TUT", 0.05, gun=0)),
    ]
    for ad, satir in dallar:
        s = satirlari_degerlendir([satir], SERI)[0]
        assert "decided_at" in s, f"{ad} dalinda decided_at anahtari YOK"
        assert s["decided_at"] == date(2026, 7, 22), (
            f"{ad} dalinda decided_at tasinmadi: {s.get('decided_at')}")


def test_olculen_bir_satir_piyasa_degerini_tasir():
    """Test anlamli olsun: gercekten olculen satirda deger DOLU olmali."""
    s = satirlari_degerlendir([_satir(1, "TUT", 0.12)], SERI)[0]
    assert s["sonuc"] == DOGRU and s["piyasa"] == pytest.approx(0.10)


# ============================================================================
# Dusmanca dogrulama turu 2 — uc gizil kusur
# ============================================================================

def test_BITIS_kapanisi_da_dogrulanir():
    """BULUNAN HATA: yalnizca baslangic kapanisi kontrol ediliyordu.

    Bitis kapanisi 0 oldugunda (s-b)/b = -1,0 doniyordu, yani "piyasa %100
    coktu" gibi UYDURMA bir olcum. Olculemeyen bir kapanisi olculmus bir
    getiriye cevirmek temel degismezin ihlalidir.
    """
    for bozuk in (0.0, -5.0):
        g, notu = piyasa_getirisi({"2026-07-22": 100.0, "2026-08-22": bozuk},
                                  date(2026, 7, 22), date(2026, 8, 22))
        assert g is None, f"bitis kapanisi {bozuk} icin {g} donduruldu"
        assert "bitis" in notu, notu


def test_baslangic_kapanisi_hala_dogrulanir():
    g, notu = piyasa_getirisi({"2026-07-22": 0.0, "2026-08-22": 110.0},
                              date(2026, 7, 22), date(2026, 8, 22))
    assert g is None and "baslangic" in notu


def test_bozuk_bitis_kapanisi_TUT_u_yanlis_damgalamaz():
    """Uctan uca: bozuk kapanis 'yanlis' degil 'olculemedi' uretmeli."""
    seri = {"2026-07-22": 100.0, "2026-08-22": 0.0}
    s = satirlari_degerlendir([_satir(1, "TUT", 0.02)], seri)[0]
    assert s["sonuc"] == OLCULEMEDI, f"uydurma getiriyle damgalandi: {s}"
    assert s["piyasa"] is None


def test_piyasa_serisi_LIMIT_gonderir():
    """BULUNAN HATA: /price varsayilan 60 bar donuyor; limit verilmezse
    seri sessizce son ~3 aya kirpilir ve eski kararlar olculemez olur."""
    import inspect

    import isabet_calistir as M
    kaynak = inspect.getsource(M.piyasa_serisi)
    assert "limit=" in kaynak, "istek limit parametresi tasimiyor"
    assert M.PIYASA_BAR_SINIRI >= 1000, (
        f"bar siniri cok dusuk: {M.PIYASA_BAR_SINIRI}")


def test_seri_cekimi_ISLEM_ACILMADAN_once():
    """BULUNAN HATA: ALTER TABLE ile ayni islem icinde 45 sn'lik HTTP cagrisi.

    DDL, hypertable ve tum parcalari uzerinde AccessExclusiveLock tutuyor;
    ayri bir veritabaninda olculdu: paralel INSERT 9,06 sn bloklandi.
    Seri cekimi 'with con' blogundan ONCE olmali.
    """
    import inspect

    import isabet_calistir as M
    kaynak = inspect.getsource(M.main)
    i_seri = kaynak.index("seri = piyasa_serisi()")
    i_islem = kaynak.index("with con,")
    assert i_seri < i_islem, (
        "piyasa_serisi() islem AcILDIKTAN sonra cagriliyor; DDL kilidi ag "
        "cagrisini bekler")
