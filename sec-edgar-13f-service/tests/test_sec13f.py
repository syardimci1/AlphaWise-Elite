"""Birim testleri: sec-edgar-13f-service."""
import asyncio
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, "/opt/alphawise/commercial/AlphaWise-Elite/sec-edgar-13f-service")

from src import ciks, cusips
from src.rate_limiter import HizSinirlayici, SEC_TAVAN_SANIYE, VARSAYILAN_HIZ

XMLNS = "{http://www.sec.gov/edgar/document/thirteenf/informationtable}"


# ==================== CIK cozumleme ====================

def test_cik_tam_eslesme():
    r = ciks.coz("vanguard")
    assert r and r[0]["cik"] == "102909"


def test_cik_blackrock_guncel_tuzel_kisi():
    """'blackrock' GUNCEL kayda (2012383) cozulmeli, 2024'te donan 1364742'ye degil."""
    r = ciks.coz("blackrock")
    assert r[0]["cik"] == "2012383"
    assert r[0]["ad"] == "BlackRock, Inc."


def test_cik_blackrock_eski_ayri_anahtar():
    """Eski tuzel kisi ayri anahtarla erisilebilir olmali (tarihsel sorgu icin)."""
    r = ciks.coz("blackrock_finance")
    assert r[0]["cik"] == "1364742"


def test_cik_bulunamayan():
    assert ciks.coz("boyle bir kurum yok 12345") == []


def test_cik_bos_sorgu():
    assert ciks.coz("") == []
    assert ciks.coz(None) == []


def test_cik_normalize_10_hane():
    """SEC submissions API 10 haneli sifir dolgulu CIK ister."""
    assert ciks.cik_normalize("102909") == "0000102909"
    assert ciks.cik_normalize("0000102909") == "0000102909"
    assert ciks.cik_normalize("2012383") == "0002012383"


def test_cik_alias_tekillestirme():
    """fidelity/fmr ve t. rowe/t rowe ayni CIK — tekil listede bir kez."""
    tum = ciks.tum_kurumlar()
    cikler = [k["cik"] for k in tum]
    assert len(cikler) == len(set(cikler)), "tum_kurumlar tekrar iceriyor"
    assert "315066" in cikler
    assert "1113169" in cikler


# ==================== CUSIP cozumleme ====================

def test_cusip_dogrulanmis_nvda():
    r = cusips.coz("NVDA")
    assert r["bulundu"] and r["cusip"] == "67066G104"
    assert r["dogrulandi"] is True


def test_cusip_kucuk_harf_ve_bosluk():
    assert cusips.coz("  nvda  ")["cusip"] == "67066G104"


def test_cusip_googl_google_farkli_sinif():
    """GOOGL (Cl A) ve GOOG (Cl C) AYRI CUSIP'lerdir — karistirilmamali."""
    a = cusips.coz("GOOGL")
    c = cusips.coz("GOOG")
    assert a["cusip"] == "02079K305"
    assert c["cusip"] == "02079K107"
    assert a["cusip"] != c["cusip"]


def test_cusip_bilinmeyen_ticker_dogrulanmadi_bayragi():
    r = cusips.coz("ZZZZ")
    assert r["bulundu"] is False
    assert r["dogrulandi"] is False


def test_normalize_amazon_com_bozulmuyor():
    """
    REGRESYON: eski normalizasyon ' CO' son ekini ALT DIZI olarak siliyordu ve
    'AMAZON COM INC' -> 'AMAZON M' oluyordu. Kelime siniriyla silinmeli.
    """
    assert cusips.normalize_ad("AMAZON COM INC") == "AMAZON COM"
    assert "M" != cusips.normalize_ad("AMAZON COM INC")


def test_normalize_sirket_son_ekleri():
    assert cusips.normalize_ad("NVIDIA CORPORATION") == "NVIDIA"
    assert cusips.normalize_ad("Apple Inc.") == "APPLE"
    assert cusips.normalize_ad("JOHNSON & JOHNSON") == "JOHNSON JOHNSON"


def test_isimle_ara_yedek_dogrulanmadi_isaretler():
    """Yedek yol her zaman dogrulandi=False dondurmeli."""
    idx = {"EXXON MOBIL": ["30231G102"]}
    r = cusips.isimle_ara("EXXON MOBIL CORP", idx)
    assert r["bulundu"] is True
    assert r["dogrulandi"] is False
    assert r["cusip"] == "30231G102"


def test_isimle_ara_bulunamayan():
    assert cusips.isimle_ara("HICBIR SEY", {})["bulundu"] is False


def test_dogrulanmis_haritada_tekrar_cusip_yok():
    """Ayni CUSIP iki ticker'a atanmis olmamali."""
    cs = [v[0] for v in cusips.DOGRULANMIS.values()]
    assert len(cs) == len(set(cs)), "DOGRULANMIS haritasinda tekrar eden CUSIP var"


def test_cusip_formati_9_karakter():
    for tk, (c, _, _) in cusips.DOGRULANMIS.items():
        assert len(c) == 9, f"{tk} CUSIP'i 9 karakter degil: {c}"


# ==================== Hiz sinirlayici ====================

def test_sinirlayici_patlama_kapasitesi_bir():
    """
    REGRESYON: kapasite=hiz (5) iken kova DOLU basliyor ve 5 istek ANINDA
    cikiyordu; es zamanli cagrilarla olculen hiz 12.19/sn'ye ciktı (SEC
    tavani 10). Varsayilan kapasite 1 olmali — patlama yok.
    """
    s = HizSinirlayici(None, hiz=5.0)
    assert s.kapasite == 1.0


def test_sinirlayici_hiz_tavanin_altinda():
    assert VARSAYILAN_HIZ < SEC_TAVAN_SANIYE


def test_sinirlayici_ilk_istek_beklemez():
    s = HizSinirlayici(None, hiz=5.0)
    assert asyncio.run(s.bekle()) == 0.0


def test_sinirlayici_ardisik_istekler_yayiliyor():
    """Es zamanli 10 cagri toplu ates ETMEMELI; 1/hiz araliklarina yayilmali."""
    async def kos():
        s = HizSinirlayici(None, hiz=5.0)
        t0 = time.monotonic()
        await asyncio.gather(*[s.bekle() for _ in range(10)])
        return time.monotonic() - t0, s.toplam_bekleme_sn

    gecen, bekleme = asyncio.run(kos())
    # 10 istek @ 5/sn -> ilk bedava, kalan 9 x 0.2 = 1.8 sn
    assert gecen >= 1.7, f"cok hizli bitti ({gecen:.2f}s) — fren calismiyor"
    assert bekleme > 0


def test_sinirlayici_rezervasyon_negatif_jeton():
    """
    REGRESYON: jeton yalnizca >=1 iken dusuluyordu. jeton=0 iken es zamanli
    gelen cagrilarin HEPSI ayni bekleme suresini alip UYKUDAN AYNI ANDA
    kalkiyordu. Jeton kosulsuz dusulmeli, negatife inebilmeli.
    """
    async def kos():
        s = HizSinirlayici(None, hiz=5.0)
        bekle = await asyncio.gather(*[s.bekle() for _ in range(5)])
        return sorted(bekle)

    b = asyncio.run(kos())
    # her cagri bir oncekinden ~0.2 sn daha uzun beklemeli
    assert b[0] == 0.0
    for i in range(1, len(b)):
        assert b[i] > b[i - 1], f"bekleme sureleri artmiyor: {b}"


def test_sinirlayici_efektif_hiz_sec_tavani_altinda():
    async def kos():
        s = HizSinirlayici(None, hiz=5.0)
        t0 = time.monotonic()
        await asyncio.gather(*[s.bekle() for _ in range(15)])
        return 15 / (time.monotonic() - t0)

    hiz = asyncio.run(kos())
    assert hiz <= SEC_TAVAN_SANIYE, f"efektif hiz {hiz:.2f}/sn SEC tavanini asiyor"


def test_sinirlayici_durum_alanlari():
    d = HizSinirlayici(None, hiz=5.0).durum()
    assert d["sec_resmi_tavan_saniyede"] == 10
    assert d["patlama_kapasitesi"] == 1.0
    assert "ONLEYICI" in d["strateji"]


# ==================== 13F ayristirma mantigi ====================

def _ornek_xml(satirlar):
    ns = "http://www.sec.gov/edgar/document/thirteenf/informationtable"
    govde = "".join(satirlar)
    return f'<informationTable xmlns="{ns}">{govde}</informationTable>'


def _satir(cusip, isim, deger, adet, sinif="COM", put_call=None):
    pc = f"<putCall>{put_call}</putCall>" if put_call else ""
    return (f"<infoTable><nameOfIssuer>{isim}</nameOfIssuer>"
            f"<titleOfClass>{sinif}</titleOfClass><cusip>{cusip}</cusip>"
            f"<value>{deger}</value>"
            f"<shrsOrPrnAmt><sshPrnamt>{adet}</sshPrnamt>"
            f"<sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>{pc}</infoTable>")


def _ayristir(xml_metin, bin_usd=False):
    """sec_client.bilgi_tablosu_ayristir'in saf (agsiz) esdegeri."""
    from collections import defaultdict
    kok = ET.fromstring(xml_metin)
    carpan = 1000 if bin_usd else 1
    poz = defaultdict(lambda: {"isim": None, "sinif": None,
                               "hisse_deger_usd": 0, "hisse_adet": 0, "hisse_satir": 0,
                               "turev_call_usd": 0, "turev_put_usd": 0, "turev_satir": 0})
    for it in kok:
        def al(t):
            e = it.find(XMLNS + t)
            return e.text if e is not None else None
        c = al("cusip")
        deger = int(al("value")) * carpan
        sh = it.find(XMLNS + "shrsOrPrnAmt")
        adet = int(sh.find(XMLNS + "sshPrnamt").text) if sh is not None else 0
        p = poz[c]
        if p["isim"] is None:
            p["isim"] = al("nameOfIssuer")
        pc = al("putCall")
        if pc:
            if pc.lower().startswith("c"):
                p["turev_call_usd"] += deger
            else:
                p["turev_put_usd"] += deger
            p["turev_satir"] += 1
        else:
            p["hisse_deger_usd"] += deger
            p["hisse_adet"] += adet
            p["hisse_satir"] += 1
            if p["sinif"] is None:
                p["sinif"] = al("titleOfClass")
    return dict(poz)


def test_ayristirma_ayni_cusip_toplanir():
    """
    KRITIK: ayni CUSIP otherManager kirilimiyla birden cok satirda gecer.
    BlackRock 2026-06-30'da NVDA 24 satirda. Toplanmazsa pozisyon eksik gorunur.
    """
    xml = _ornek_xml([
        _satir("67066G104", "NVIDIA CORPORATION", 100, 10),
        _satir("67066G104", "NVIDIA CORPORATION", 250, 25),
        _satir("67066G104", "NVIDIA CORPORATION", 650, 65),
    ])
    p = _ayristir(xml)["67066G104"]
    assert p["hisse_deger_usd"] == 1000
    assert p["hisse_adet"] == 100
    assert p["hisse_satir"] == 3


def test_ayristirma_turev_hisseye_karismaz():
    """
    KRITIK: putCall dolu satirlar opsiyondur. Hisseyle toplanirsa deger sisirilir.
    """
    xml = _ornek_xml([
        _satir("67066G104", "NVIDIA CORPORATION", 1000, 100),
        _satir("67066G104", "NVIDIA CORPORATION", 500, 50, "OPTIONS", "Call"),
        _satir("67066G104", "NVIDIA CORPORATION", 300, 30, "OPTIONS", "Put"),
    ])
    p = _ayristir(xml)["67066G104"]
    assert p["hisse_deger_usd"] == 1000, "turev hisse degerine karismis"
    assert p["hisse_adet"] == 100
    assert p["turev_call_usd"] == 500
    assert p["turev_put_usd"] == 300
    assert p["turev_satir"] == 2


def test_ayristirma_sinif_hisseden_alinir():
    """titleOfClass turev satirindan degil, hisse satirindan alinmali."""
    xml = _ornek_xml([
        _satir("67066G104", "NVIDIA CORPORATION", 1000, 100, "COM"),
        _satir("67066G104", "NVIDIA CORPORATION", 500, 50, "OPTIONS", "Call"),
    ])
    assert _ayristir(xml)["67066G104"]["sinif"] == "COM"


def test_ayristirma_deger_birimi_2023_oncesi():
    """
    KRITIK: 2023 oncesi <value> BIN USD. Normalize edilmezse 1000 kat hata.
    """
    xml = _ornek_xml([_satir("67066G104", "NVIDIA CORPORATION", 1000, 100)])
    eski = _ayristir(xml, bin_usd=True)["67066G104"]
    yeni = _ayristir(xml, bin_usd=False)["67066G104"]
    assert eski["hisse_deger_usd"] == 1_000_000
    assert yeni["hisse_deger_usd"] == 1_000
    assert eski["hisse_deger_usd"] == yeni["hisse_deger_usd"] * 1000


def test_ayristirma_coklu_cusip_ayrisir():
    xml = _ornek_xml([
        _satir("67066G104", "NVIDIA CORPORATION", 1000, 100),
        _satir("037833100", "APPLE INC", 2000, 200),
    ])
    p = _ayristir(xml)
    assert len(p) == 2
    assert p["67066G104"]["hisse_deger_usd"] == 1000
    assert p["037833100"]["hisse_deger_usd"] == 2000


# ==================== Bilgi tablosu dosya secimi ====================

def _tablo_sec(ogeler):
    """sec_client.bilgi_tablosu_url'deki secim mantiginin saf esdegeri."""
    adaylar = [o for o in ogeler
               if o["name"].lower().endswith(".xml")
               and "primary_doc" not in o["name"].lower()]
    if not adaylar:
        return None
    adaylar.sort(key=lambda o: int(o.get("size") or 0), reverse=True)
    return adaylar[0]["name"]


def test_tablo_secimi_primary_doc_atlanir():
    """primary_doc.xml kapak sayfasidir, pozisyon icermez."""
    r = _tablo_sec([
        {"name": "primary_doc.xml", "size": "5555"},
        {"name": "form13fInfoTable.xml", "size": "23016794"},
    ])
    assert r == "form13fInfoTable.xml"


def test_tablo_secimi_rastgele_ad():
    """Dosya adi kuruma gore degisir (Berkshire'da 56757.xml) — tahmin edilemez."""
    r = _tablo_sec([
        {"name": "primary_doc.xml", "size": "5555"},
        {"name": "56757.xml", "size": "44724"},
    ])
    assert r == "56757.xml"


def test_tablo_secimi_en_buyugu():
    r = _tablo_sec([
        {"name": "kucuk.xml", "size": "100"},
        {"name": "buyuk.xml", "size": "999999"},
    ])
    assert r == "buyuk.xml"


def test_tablo_secimi_xml_yoksa_none():
    assert _tablo_sec([{"name": "primary_doc.xml", "size": "5"}]) is None


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.run(
        ["python3", "-m", "pytest", __file__, "-v"], check=False).returncode)
