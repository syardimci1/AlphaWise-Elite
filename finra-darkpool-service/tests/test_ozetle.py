"""
finra.ozetle() birim testleri.
Ana amac: ats_orani_yuzde alaninin bir daha %100'u ASMAMASI (SPY hatasi regresyonu).
Ag erisimi yok - ozetle() saf fonksiyondur, ham kayit listesi alir.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import finra


def _kayit(tip, shares, trades=100, mpid=None, ad=None):
    r = {
        "summaryTypeCode": tip,
        "totalWeeklyShareQuantity": shares,
        "totalWeeklyTradeCount": trades,
        "issueName": "TEST INC",
        "tierIdentifier": "T1",
    }
    if mpid:
        r["MPID"] = mpid
    if ad:
        r["marketParticipantName"] = ad
    return r


def test_spy_senaryosu_yuzde_yuz_asilmaz():
    # Gercek SPY (2026-07-27): ATS=84,159,736  OTC=53,304,140
    # Eski formul: 84.16M/53.30M*100 = 157.89 (IMKANSIZ)
    # Dogru formul: 84.16M/(84.16M+53.30M)*100 = 61.22
    kayitlar = [
        _kayit("ATS_W_SMBL", 84159736),
        _kayit("OTC_W_SMBL", 53304140),
    ]
    o = finra.ozetle("SPY", "2026-07-27", kayitlar)
    assert o["ats_orani_yuzde"] == 61.22
    assert 0 <= o["ats_orani_yuzde"] <= 100
    assert o["borsa_disi_toplam_shares"] == 84159736 + 53304140


def test_ats_otc_esitse_elli():
    kayitlar = [_kayit("ATS_W_SMBL", 1000), _kayit("OTC_W_SMBL", 1000)]
    o = finra.ozetle("X", "2026-07-27", kayitlar)
    assert o["ats_orani_yuzde"] == 50.0


def test_tum_hacim_ats_ise_yuz():
    kayitlar = [_kayit("ATS_W_SMBL", 5000), _kayit("OTC_W_SMBL", 0)]
    o = finra.ozetle("X", "2026-07-27", kayitlar)
    assert o["ats_orani_yuzde"] == 100.0


def test_hic_ats_yoksa_sifir():
    kayitlar = [_kayit("ATS_W_SMBL", 0), _kayit("OTC_W_SMBL", 4000)]
    o = finra.ozetle("X", "2026-07-27", kayitlar)
    assert o["ats_orani_yuzde"] == 0.0


def test_hic_veri_yoksa_none():
    o = finra.ozetle("X", "2026-07-27", [])
    assert o["ats_orani_yuzde"] is None
    assert o["borsa_disi_toplam_shares"] == 0
    assert o["veri_var"] is False


def test_venue_ici_pay_hesaplanir():
    kayitlar = [
        _kayit("ATS_W_SMBL", 1000),
        _kayit("OTC_W_SMBL", 1000),
        _kayit("ATS_W_SMBL_FIRM", 600, mpid="AAAA", ad="Havuz A"),
        _kayit("ATS_W_SMBL_FIRM", 400, mpid="BBBB", ad="Havuz B"),
    ]
    o = finra.ozetle("X", "2026-07-27", kayitlar)
    assert o["venues"][0]["mpid"] == "AAAA"
    assert o["venues"][0]["ats_ici_pay_yuzde"] == 60.0
    assert o["dark_pool"]["aktif_ats_sayisi"] == 2


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
