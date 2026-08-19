"""
Birim testleri: kalibrasyon metrigi.

Bu testlerin cogu REGRESYON testidir: duzeltilen "isabet - baz"
karsilastirma hatasini kilitler. Her biri, hatali metrik geri
konuldugunda KIRMIZI olacak sekilde yazilmistir (negatif kontrol
calisma raporunda gosterilmistir).
"""
import math
import sys

sys.path.insert(0, "/opt/alphawise/commercial/AlphaWise-Elite/liquidity-signal-service")

from calibration.kalibre import (
    beceri, eski_hatali_metrik, veri_yukle, skor_serisi,
    zskor, yoy, momentum, rejim, kompozit_skor, ffill,
    EGITIM, TEST, GECME_ESIGI_PUAN,
)
from src.kalibrasyon import KALIBRASYON


# ==================== yapay veriyle metrik dogrulugu ====================

def _kur(gun_sayisi, skor_deseni, fiyat_deseni):
    gunler = [f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(gun_sayisi)]
    return gunler, skor_deseni, fiyat_deseni


def test_beceri_mukemmel_sinyal_pozitif():
    """Her seferinde dogru yonu soyleyen sinyal POZITIF beceri vermeli."""
    n = 200
    gunler = [f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(n)]
    # fiyat: donusumlu yukari/asagi
    fiyat = []
    p = 100.0
    for i in range(n):
        p = p * 1.02 if i % 2 == 0 else p * 0.98
        fiyat.append(p)
    # skor: bir sonraki adimi bilen mukemmel sinyal (ufuk=1)
    skor = [1.0 if (i + 1) % 2 == 0 else -1.0 for i in range(n)]
    r = beceri(gunler, skor, fiyat, 1, gunler[0], gunler[-1])
    assert r["beceri_puan"] > 30, f"mukemmel sinyal dusuk beceri verdi: {r['beceri_puan']}"


def test_beceri_rastgele_sinyal_sifira_yakin():
    """Fiyattan bagimsiz donusumlu sinyal ~0 beceri vermeli."""
    n = 400
    gunler = [f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(n)]
    p = 100.0
    fiyat = []
    for i in range(n):
        p = p * (1.01 if (i * 7) % 3 else 0.99)
        fiyat.append(p)
    skor = [1.0 if i % 2 == 0 else -1.0 for i in range(n)]
    r = beceri(gunler, skor, fiyat, 1, gunler[0], gunler[-1])
    assert abs(r["beceri_puan"]) < 20


def test_beceri_asagi_sinyali_dogru_referansla_olculur():
    """
    REGRESYON — DUZELTILEN HATA.

    Yukselen bir piyasada (baz=%80) SADECE asagi sinyali uretilsin ve
    sans karsiligi kadar (%20) isabet etsin. Dogru metrik ~0 beceri
    vermelidir. Eski metrik ayni durumu -60 puan gibi gosteriyordu.
    """
    n = 500
    gunler = [f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(n)]
    # %80 gun yukari
    fiyat = [100.0]
    for i in range(n):
        fiyat.append(fiyat[-1] * (1.01 if i % 5 != 0 else 0.99))
    skor = [-1.0] * n  # her gun ASAGI sinyali

    dogru = beceri(gunler, skor, fiyat, 1, gunler[0], gunler[-1])
    hatali = eski_hatali_metrik(gunler, skor, fiyat, 1, gunler[0], gunler[-1])

    assert abs(dogru["beceri_puan"]) < 5, \
        f"dogru metrik sans seviyesinde ~0 vermeli, verdi: {dogru['beceri_puan']:.2f}"
    assert hatali["fark_puan"] < -50, \
        f"eski metrik burada buyuk negatif vermeliydi: {hatali['fark_puan']:.2f}"
    assert dogru["beceri_puan"] - hatali["fark_puan"] > 50, \
        "eski metrigin abartisi gosterilemedi"


def test_beklenen_dogru_formulu():
    """beklenen_dogru = n_yukari*baz + n_asagi*(1-baz)"""
    n = 300
    gunler = [f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(n)]
    fiyat = [100.0]
    for i in range(n):
        fiyat.append(fiyat[-1] * (1.01 if i % 4 else 0.99))
    skor = [1.0 if i % 3 == 0 else -1.0 for i in range(n)]
    r = beceri(gunler, skor, fiyat, 1, gunler[0], gunler[-1])
    beklenen = r["n_yukari"] * r["baz_oran"] + r["n_asagi"] * (1 - r["baz_oran"])
    assert abs(r["beklenen_dogru"] - beklenen) < 1e-9


def test_beceri_tarafsiz_piyasada_iki_metrik_yakinlasir():
    """
    baz=%50 iken YUKARI ve ASAGI'nin sans karsiligi esittir; iki metrik
    birbirine yakinsamali. Hatanin YALNIZCA dengesiz piyasada ortaya
    ciktigini gosterir.
    """
    n = 400
    gunler = [f"2024-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(n)]
    fiyat = [100.0]
    for i in range(n):
        fiyat.append(fiyat[-1] * (1.01 if i % 2 == 0 else 0.99))
    skor = [1.0 if i % 3 == 0 else -1.0 for i in range(n)]
    d = beceri(gunler, skor, fiyat, 1, gunler[0], gunler[-1])
    h = eski_hatali_metrik(gunler, skor, fiyat, 1, gunler[0], gunler[-1])
    assert abs(d["baz_oran"] - 0.5) < 0.05
    assert abs(d["beceri_puan"] - h["fark_puan"]) < 6


def test_beceri_sinyal_yoksa_none():
    gunler = [f"2024-01-{1 + i:02d}" for i in range(10)]
    fiyat = [100.0] * 12
    skor = [0.0] * 10  # hicbiri esigi gecmiyor
    assert beceri(gunler, skor, fiyat, 1, gunler[0], gunler[-1]) is None


# ==================== gercek veriyle uctan uca ====================

def test_gercek_veri_yuklenebiliyor():
    gunler, net_lik, varliklar = veri_yukle()
    assert len(gunler) > 1000
    assert set(varliklar) == {"NASDAQ", "SP500", "BTC"}
    assert sum(1 for v in net_lik if v is not None) > 1000


def test_gercek_kalibrasyon_hicbir_spek_gecmiyor():
    """
    DURUSTLUK KILIDI: bu test, birileri esigi dusurerek ya da metrigi
    gevseterek sahte bir 'gecti' uretirse KIRMIZI olur.
    """
    gunler, net_lik, varliklar = veri_yukle()
    gecen = 0
    for ad, fiyat in varliklar.items():
        skor = skor_serisi(net_lik, fiyat)
        for h in (5, 10, 20):
            r = beceri(gunler, skor, fiyat, h, *TEST)
            if r and r["beceri_puan"] >= GECME_ESIGI_PUAN:
                gecen += 1
    assert gecen == 0, f"{gecen} spesifikasyon gecti — kalibrasyon.py guncellenmeli"


def test_gercek_veri_beceri_araligi():
    """Olculen beceri araligi kalibrasyon.py'de yazan ile TUTARLI olmali."""
    gunler, net_lik, varliklar = veri_yukle()
    puanlar = []
    for ad, fiyat in varliklar.items():
        skor = skor_serisi(net_lik, fiyat)
        for h in (5, 10, 20):
            r = beceri(gunler, skor, fiyat, h, *TEST)
            if r:
                puanlar.append(r["beceri_puan"])
    assert len(puanlar) == 9
    assert abs(max(puanlar) - KALIBRASYON["en_iyi_beceri_puan"]) < 0.01
    assert abs(min(puanlar) - KALIBRASYON["en_kotu_beceri_puan"]) < 0.01


def test_eski_metrik_abartisi_belgelendigi_gibi():
    """kalibrasyon.py 'ortalama 17.11 puan abarti' diyor — dogrula."""
    gunler, net_lik, varliklar = veri_yukle()
    abartilar = []
    for ad, fiyat in varliklar.items():
        skor = skor_serisi(net_lik, fiyat)
        for h in (5, 10, 20):
            d = beceri(gunler, skor, fiyat, h, *TEST)
            e = eski_hatali_metrik(gunler, skor, fiyat, h, *TEST)
            abartilar.append(d["beceri_puan"] - e["fark_puan"])
    ort = sum(abartilar) / len(abartilar)
    assert abs(ort - KALIBRASYON["metrik"]["abarti_ortalama_puan"]) < 0.05
    assert ort > 0, "eski metrik her zaman daha kotu gostermeliydi"


# ==================== servis durumu tutarliligi ====================

def test_servis_deneysel_isaretli():
    assert KALIBRASYON["durum"] == "deneysel"
    assert KALIBRASYON["gecerli"] is False
    assert KALIBRASYON["yon_kodu_uretir"] is False
    assert KALIBRASYON["buzusme_lambda"] == 0.0


def test_lambda_ancak_gecen_spek_varsa_artabilir():
    """
    DURUSTLUK KILIDI: basarili_spesifikasyon=0 iken lambda>0 olamaz.
    """
    if KALIBRASYON["basarili_spesifikasyon"] == 0:
        assert KALIBRASYON["buzusme_lambda"] == 0.0
        assert KALIBRASYON["gecerli"] is False


def test_kalibrasyon_yeniden_uretim_yolu_var():
    """Iddia eden her sayinin ureten betigi belgede olmali."""
    assert "calibration/kalibre.py" in KALIBRASYON["yeniden_uret"]
    import os
    yol = os.path.join(
        "/opt/alphawise/commercial/AlphaWise-Elite/liquidity-signal-service",
        "calibration", "kalibre.py")
    assert os.path.exists(yol), "kalibrasyon betigi depoda yok"


def test_elenen_alternatifler_belgelenmis():
    e = KALIBRASYON["elenen_alternatifler"]
    for anahtar in ("esik_ayari", "isaret_cevirme", "orneklem"):
        assert anahtar in e and len(e[anahtar]) > 20


# ==================== faktor fonksiyonlari ====================

def test_zskor_sabit_seride_none():
    assert zskor([5.0] * 20)[-1] is None


def test_zskor_bilinen_deger():
    s = [1.0, 2.0, 3.0, 4.0, 5.0]
    z = zskor(s, 60)[-1]
    # ortalama 3, ornek sd = sqrt(2.5) = 1.5811
    assert abs(z - (5 - 3) / math.sqrt(2.5)) < 1e-9


def test_yoy_periyot_oncesi_none():
    assert yoy([1.0] * 100, 252)[-1] is None


def test_momentum_hesabi():
    s = [100.0] * 20 + [110.0]
    assert abs(momentum(s, 20)[-1] - 10.0) < 1e-9


def test_ffill_ileriye_tasiyor():
    gunler = ["2024-01-01", "2024-01-02", "2024-01-03"]
    seri = {"2024-01-01": 5.0}
    assert ffill(gunler, seri) == [5.0, 5.0, 5.0]


def test_ffill_veri_oncesi_none():
    gunler = ["2024-01-01", "2024-01-02"]
    assert ffill(gunler, {"2024-01-02": 7.0}) == [None, 7.0]


def test_kompozit_skor_araligi():
    """Kompozit skor -1.8 .. +1.8 araliginda kalmali."""
    for rej in ("genisleme_hizlaniyor", "genisleme_yavasliyor",
                "daralma_hizlaniyor", "daralma_yavasliyor", "tanimsiz"):
        for sz in (-3.0, 0.0, 3.0):
            for dev in (-3.0, 0.0, 3.0):
                for lm in (-5.0, 5.0):
                    for pm in (-5.0, 5.0):
                        s = kompozit_skor(rej, sz, dev, lm, pm)
                        assert -1.8 <= s <= 1.8


def test_kompozit_skor_none_girdilerle_calisir():
    assert kompozit_skor("tanimsiz", None, None, None, None) == 0.0


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.run(
        ["python3", "-m", "pytest", __file__, "-v"], check=False).returncode)
