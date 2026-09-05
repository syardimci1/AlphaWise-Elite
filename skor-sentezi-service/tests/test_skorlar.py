"""
Bes eksenli skor sentezinin regresyon agi.

Beklenen degerler UYGULAMADAN BAGIMSIZ turetildi: Altman/Piotroski/Beneish
icin elle hesaplandi, DCF icin uygulamadaki dongu yerine KAPALI FORMLU
anuite formulu kullanildi. Boylece test, kodun kendi hatasini onaylamaz.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from src.skorlar import (Donem, Sirket, altman_z, piotroski_f, beneish_m,
                         dcf_icsel_fiyat_orani, temettu_dayanikligi)
from src import normalizasyon as N
from src.sentez import sentezle, ASGARI_EKSEN
from src.olcum import Olcum, olculdu, olculemedi, uygulanamaz, OLCULDU, OLCULEMEDI, UYGULANAMAZ


def _anayasa_yolu():
    """maa/src/constitution.py'yi hem host'ta (goreli) hem de test
    konteynerinde (/repo baglantisi) bulur. Yalnizca goreli yola bakan ilk
    surum, konteynerde dosyayi bulamayip testi SESSIZCE ATLIYORDU; atlanan
    bir sozlesme testi, gecmis gibi gorunen bir bosluktur."""
    adaylar = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "maa", "src", "constitution.py"),
        "/repo/maa/src/constitution.py",
        os.path.join(os.environ.get("DEPO_KOK", ""), "maa", "src", "constitution.py"),
    ]
    for y in adaylar:
        if y and os.path.exists(y):
            return y
    return None


# ============================================================ olcum sozlesmesi
def test_olculdu_none_deger_kabul_etmez():
    with pytest.raises(ValueError):
        Olcum(deger=None, durum=OLCULDU)


def test_olculemedi_sifir_yazmaya_izin_vermez():
    """Bu, 232d1a0'da kapatilan hatanin tip duzeyinde kilididir: eksik olcume
    0 yazmak 'olculdu ve notr' demektir."""
    with pytest.raises(ValueError):
        Olcum(deger=0.0, durum=OLCULEMEDI)
    with pytest.raises(ValueError):
        Olcum(deger=0.0, durum=UYGULANAMAZ)


def test_gercek_sifir_olculdu_olarak_gecerlidir():
    o = olculdu(0.0)
    assert o.var_mi and o.deger == 0.0


# ==================================================================== ALTMAN Z
def altman_sirketi(**degisiklik):
    b = {"Total Assets": 1000.0, "Working Capital": 200.0, "Retained Earnings": 300.0,
         "Total Liabilities Net Minority Interest": 400.0}
    g = {"EBIT": 150.0, "Total Revenue": 900.0}
    b.update(degisiklik.pop("bilanco", {})); g.update(degisiklik.pop("gelir", {}))
    piyasa = {"piyasa_degeri": 2000.0}; piyasa.update(degisiklik.pop("piyasa", {}))
    return Sirket("TEST", [Donem("2026", bilanco=b, gelir=g)], piyasa=piyasa)


def test_altman_z_elle_hesaplanan_degeri_verir():
    """X1=.2 X2=.3 X3=.15 X4=5.0 X5=.9
    Z = 1.2(.2)+1.4(.3)+3.3(.15)+0.6(5)+1.0(.9)
      = .24+.42+.495+3.0+.9 = 5.055"""
    o = altman_z(altman_sirketi())
    assert o.durum == OLCULDU
    assert o.deger == pytest.approx(5.055, abs=1e-9)
    assert o.ayrinti["X4"] == pytest.approx(5.0)


def test_altman_bankaya_UYGULANAMAZ_doner_olculemedi_degil():
    s = altman_sirketi(piyasa={"sektor": "Financial Services"})
    o = altman_z(s)
    assert o.durum == UYGULANAMAZ
    assert o.deger is None
    assert "banka" in o.gerekce.lower() or "finansal" in o.gerekce.lower()


def test_altman_eksik_kalemde_olculemedi_ve_eksigi_ADIYLA_bildirir():
    s = altman_sirketi(); del s.donemler[0].gelir["EBIT"]
    o = altman_z(s)
    assert o.durum == OLCULEMEDI and o.deger is None
    assert "EBIT" in o.eksik


def test_altman_isletme_sermayesi_yoksa_cari_kalemlerden_turetilir():
    s = altman_sirketi()
    del s.donemler[0].bilanco["Working Capital"]
    s.donemler[0].bilanco.update({"Current Assets": 500.0, "Current Liabilities": 300.0})
    o = altman_z(s)
    assert o.durum == OLCULDU and o.ayrinti["X1"] == pytest.approx(0.2)


# ================================================================= PIOTROSKI F
def piotroski_sirketi():
    t2 = Donem("2024", bilanco={"Total Assets": 800.0})
    t1 = Donem("2025",
               bilanco={"Total Assets": 900.0, "Long Term Debt": 100.0,
                        "Current Assets": 300.0, "Current Liabilities": 200.0,
                        "Ordinary Shares Number": 100.0},
               gelir={"Net Income": 90.0, "Gross Profit": 280.0, "Total Revenue": 700.0})
    t = Donem("2026",
              bilanco={"Total Assets": 1000.0, "Long Term Debt": 80.0,
                       "Current Assets": 400.0, "Current Liabilities": 200.0,
                       "Ordinary Shares Number": 100.0},
              gelir={"Net Income": 120.0, "Gross Profit": 400.0, "Total Revenue": 900.0},
              nakit={"Operating Cash Flow": 200.0})
    return Sirket("TEST", [t, t1, t2])


def test_piotroski_dokuz_kriterin_hepsi_saglanan_sirkette_9_verir():
    """Elle: ROA_t=120/900=.1333>0 (1); CFO=200>0 (2); ROA_t1=90/800=.1125,
    artti (3); CFO/TA_t1=.2222>ROA_t (4); kaldirac .08<.1111 (5);
    cari 2.0>1.5 (6); hisse 100<=100 (7); marj .4444>.40 (8);
    devir 1.0>0.875 (9) -> 9"""
    o = piotroski_f(piotroski_sirketi())
    assert o.durum == OLCULDU and o.deger == 9.0
    assert all(o.ayrinti[k] for k in
               ("roa_pozitif", "cfo_pozitif", "roa_artti", "tahakkuk_kalitesi",
                "kaldirac_azaldi", "likidite_artti", "yeni_hisse_ihraci_yok",
                "brut_marj_artti", "varlik_devri_artti"))


def test_piotroski_tek_kriter_bozulunca_8_olur():
    s = piotroski_sirketi()
    s.donemler[0].bilanco["Ordinary Shares Number"] = 120.0  # yeni hisse ihraci
    o = piotroski_f(s)
    assert o.deger == 8.0 and o.ayrinti["yeni_hisse_ihraci_yok"] is False


def test_piotroski_iki_donemle_KISMI_skor_uretmez():
    s = piotroski_sirketi(); s.donemler = s.donemler[:2]
    o = piotroski_f(s)
    assert o.durum == OLCULEMEDI and o.deger is None and "3 mali donem" in o.gerekce


# =================================================================== BENEISH M
def beneish_sirketi():
    """t ve t-1 tum oranlarda AYNI -> sekiz endeksin yedisi tam olarak 1.0;
    yalnizca TATA sifirdan farkli."""
    ortak_b = {"Receivables": 100.0, "Current Assets": 400.0, "Net PPE": 300.0,
               "Total Assets": 1000.0, "Current Liabilities": 200.0,
               "Long Term Debt": 100.0}
    ortak_g = {"Total Revenue": 900.0, "Cost Of Revenue": 500.0,
               "Selling General And Administration": 100.0, "Net Income": 120.0}
    ortak_n = {"Depreciation And Amortization": 50.0, "Operating Cash Flow": 200.0}
    return Sirket("TEST", [
        Donem("2026", bilanco=dict(ortak_b), gelir=dict(ortak_g), nakit=dict(ortak_n)),
        Donem("2025", bilanco=dict(ortak_b), gelir=dict(ortak_g), nakit=dict(ortak_n)),
    ])


def test_beneish_m_elle_hesaplanan_degeri_verir():
    """Yedi endeks 1.0, TATA=(120-200)/1000=-0.08.
    Sabit toplam = -4.84+0.920+0.528+0.404+0.892+0.115-0.172-0.327 = -2.480
    M = -2.480 + 4.679*(-0.08) = -2.85432"""
    o = beneish_m(beneish_sirketi())
    assert o.durum == OLCULDU
    for e in ("DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "LVGI"):
        assert o.ayrinti[e] == pytest.approx(1.0), e
    assert o.ayrinti["TATA"] == pytest.approx(-0.08)
    assert o.deger == pytest.approx(-2.85432, abs=1e-9)


def test_beneish_tek_donemle_olculemedi():
    s = beneish_sirketi(); s.donemler = s.donemler[:1]
    assert beneish_m(s).durum == OLCULEMEDI


# ========================================================================= DCF
def dcf_sirketi(fiyat=10.0):
    b = {"Total Debt": 200.0, "Cash And Cash Equivalents": 50.0}
    return Sirket("TEST", [
        Donem("2026", bilanco=b, nakit={"Free Cash Flow": 100.0}),
        Donem("2025", bilanco=b, nakit={"Free Cash Flow": 100.0}),
    ], piyasa={"beta": 1.0, "fiyat": fiyat, "hisse_adedi": 100.0})


def test_dcf_kapali_formlu_anuite_ile_ayni_sonucu_verir():
    """BAGIMSIZ TURETME: uygulama yil yil dongu kurar; burada kapali formlu
    anuite kullanilir.
      g=0 (100->100 buyume yok), r = 0.04 + 1.0*0.05 = 0.09
      PV(5 esit odeme) = C * (1-(1+r)^-5)/r
      Terminal = C*(1+g_sonsuz)/(r-g_sonsuz), 5. yildan bugune indirgenir
    """
    r, C, gs, n = 0.09, 100.0, 0.025, 5
    pv_acik = C * (1 - (1 + r) ** -n) / r
    pv_terminal = (C * (1 + gs) / (r - gs)) / (1 + r) ** n
    ozkaynak = pv_acik + pv_terminal - (200.0 - 50.0)
    icsel_beklenen = ozkaynak / 100.0
    beklenen_oran = icsel_beklenen / 10.0

    o = dcf_icsel_fiyat_orani(dcf_sirketi(), risksiz_faiz=0.04)
    assert o.durum == OLCULDU
    assert o.ayrinti["icsel_deger"] == pytest.approx(icsel_beklenen, rel=1e-9)
    assert o.deger == pytest.approx(beklenen_oran, rel=1e-9)
    assert o.ayrinti["iskonto_orani"] == pytest.approx(0.09)
    # Klasik guvenlik payi ayrinti icinde YINE de bildirilir
    assert o.ayrinti["klasik_guvenlik_payi"] == pytest.approx(
        (icsel_beklenen - 10.0) / icsel_beklenen, rel=1e-9)


def test_dcf_risksiz_faiz_yoksa_olculemedi():
    assert dcf_icsel_fiyat_orani(dcf_sirketi(), risksiz_faiz=None).durum == OLCULEMEDI


def test_dcf_negatif_nakit_akisinda_olculemedi():
    s = dcf_sirketi(); s.donemler[0].nakit["Free Cash Flow"] = -50.0
    o = dcf_icsel_fiyat_orani(s, risksiz_faiz=0.04)
    assert o.durum == OLCULEMEDI and "pozitif degil" in o.gerekce


def test_dcf_fiyat_yuksekse_oran_birin_altina_duser():
    o = dcf_icsel_fiyat_orani(dcf_sirketi(fiyat=100.0), risksiz_faiz=0.04)
    assert o.durum == OLCULDU and o.deger < 1.0


def test_dcf_olcutu_sifir_ozkaynak_civarinda_SUREKLIDIR():
    """CANLI OLCUMDE BULUNAN HATA: klasik guvenlik payi (icsel-fiyat)/icsel,
    icsel deger sifira yaklasirken -sonsuza gidiyor, sifirin altinda ise kod
    -1.0'e atliyordu. Yani neredeyse ayni iki sirket -31.79 ve -1.0 aliyordu.
    Yeni olcut (icsel/fiyat) sifirin her iki yaninda SUREKLI olmali."""
    def oran_ile(net_borc):
        s = dcf_sirketi()
        s.donemler[0].bilanco["Total Debt"] = net_borc + 50.0
        return dcf_icsel_fiyat_orani(s, risksiz_faiz=0.04).deger

    # Ozkaynagi sifira cok yakin iki nokta secelim: ozkaynak = PV - net_borc
    from src.skorlar import _al
    pv = None
    o = dcf_icsel_fiyat_orani(dcf_sirketi(), risksiz_faiz=0.04)
    pv = o.ayrinti["icsel_deger"] * 100.0 + o.ayrinti["net_borc"]
    hemen_ustu = oran_ile(pv - 1.0)     # ozkaynak = +1
    hemen_altinda = oran_ile(pv + 1.0)  # ozkaynak = -1
    assert abs(hemen_ustu - hemen_altinda) < 0.05, (
        f"sifir civarinda sicrama var: {hemen_ustu} vs {hemen_altinda}")
    assert hemen_altinda < 0, "negatif ozkaynak negatif oran vermeli"


# ==================================================================== TEMETTU
def temettu_sirketi(temettu=-40.0, ni=100.0, fcf=100.0, yil=10):
    return Sirket("TEST", [Donem("2026", gelir={"Net Income": ni},
                                 nakit={"Cash Dividends Paid": temettu,
                                        "Free Cash Flow": fcf})],
                  piyasa={"temettu_kesintisiz_yil": yil})


def test_temettu_odemeyen_sirket_UYGULANAMAZ_sifir_degil():
    """Buyume sirketini 0 puanla cezalandirmak, 'temettusu yok' ile
    'temettusu surdurulemez'i karistirmak olurdu."""
    s = Sirket("TEST", [Donem("2026", gelir={"Net Income": 100.0},
                              nakit={"Free Cash Flow": 100.0})], piyasa={})
    o = temettu_dayanikligi(s)
    assert o.durum == UYGULANAMAZ and o.deger is None


def test_temettu_saglam_odeyicide_yuksek_puan():
    """odeme orani .40 -> bilesen 100; fcf orani .40 -> 100; 10/20 yil -> 50
    puan = .4*100 + .4*100 + .2*50 = 90"""
    o = temettu_dayanikligi(temettu_sirketi())
    assert o.durum == OLCULDU and o.deger == pytest.approx(90.0)


def test_temettu_zarardaki_sirkette_sifir_ve_bu_GERCEK_olcumdur():
    o = temettu_dayanikligi(temettu_sirketi(ni=-10.0))
    assert o.durum == OLCULDU
    assert o.ayrinti["bilesen_odeme"] == 0.0


# =============================================================== NORMALIZASYON
def test_altman_capalari_yayimlanmis_esiklere_oturur():
    assert N.altman_puan(1.81) == pytest.approx(30.0)
    assert N.altman_puan(2.99) == pytest.approx(70.0)
    assert N.altman_puan(-5) == 0.0 and N.altman_puan(99) == 100.0


def test_beneish_puani_TERSTIR():
    assert N.beneish_puan(-1.78) == pytest.approx(50.0)
    assert N.beneish_puan(-3.0) == 100.0
    assert N.beneish_puan(0.0) == 0.0
    assert N.beneish_puan(-2.5) > N.beneish_puan(-2.0), "dusuk M daha iyi olmali"


def test_piotroski_puani_dogrusaldir():
    assert N.piotroski_puan(9) == pytest.approx(100.0)
    assert N.piotroski_puan(0) == 0.0
    assert N.piotroski_puan(4.5) == pytest.approx(50.0)


def test_dcf_puani_fiyat_icsel_degere_esitken_50():
    assert N.dcf_puan(1.0) == pytest.approx(50.0)
    assert N.dcf_puan(0.0) == 0.0, "icsel deger sifirsa puan sifir"
    assert N.dcf_puan(-3.0) == 0.0, "negatif ozkaynak da sifir (kirpilir)"
    assert N.dcf_puan(2.0) == pytest.approx(100.0)
    assert N.dcf_puan(1.5) > N.dcf_puan(1.2), "oran arttikca puan artmali"


# ======================================================================= SENTEZ
def tam_sirket():
    p = piotroski_sirketi()
    p.donemler[0].bilanco.update({"Working Capital": 200.0, "Retained Earnings": 300.0,
                                  "Total Liabilities Net Minority Interest": 400.0,
                                  "Receivables": 100.0, "Net PPE": 300.0,
                                  "Total Debt": 200.0, "Cash And Cash Equivalents": 50.0})
    p.donemler[0].gelir.update({"EBIT": 150.0, "Cost Of Revenue": 500.0,
                                "Selling General And Administration": 100.0})
    p.donemler[0].nakit.update({"Free Cash Flow": 100.0,
                                "Depreciation And Amortization": 50.0,
                                "Cash Dividends Paid": -40.0})
    p.donemler[1].bilanco.update({"Receivables": 100.0, "Net PPE": 300.0})
    p.donemler[1].gelir.update({"Cost Of Revenue": 400.0,
                                "Selling General And Administration": 80.0})
    p.donemler[1].nakit.update({"Free Cash Flow": 100.0,
                                "Depreciation And Amortization": 50.0,
                                "Operating Cash Flow": 150.0})
    p.piyasa = {"piyasa_degeri": 2000.0, "beta": 1.0, "fiyat": 10.0,
                "hisse_adedi": 100.0, "temettu_kesintisiz_yil": 10}
    return p


def test_sentez_bes_ekseni_de_dondurur():
    s = sentezle(tam_sirket(), risksiz_faiz=0.04)
    assert len(s["eksenler"]) == 5
    assert [e["anahtar"] for e in s["eksenler"]] == [
        "finansal_saglik", "kazanc_kalitesi", "temel_guc", "degerleme", "temettu"]


def test_sentez_olculemeyen_ekseni_ASLA_sifir_yazmaz():
    s = sentezle(tam_sirket(), risksiz_faiz=None)  # DCF olculemez
    dcf = [e for e in s["eksenler"] if e["anahtar"] == "degerleme"][0]
    assert dcf["durum"] == OLCULEMEDI
    assert dcf["puan"] is None, "olculemeyen eksene 0 yazmak yasak"


def test_sentez_ucten_az_eksende_GENEL_PUAN_URETMEZ():
    """Anayasa Madde 2.1 ile ayni ilke: 3'ten az katman -> karar yok."""
    bos = Sirket("BOS", [Donem("2026")], piyasa={})
    s = sentezle(bos, risksiz_faiz=None)
    assert s["genel_puan"] is None
    assert s["olculebilen_eksen"] < ASGARI_EKSEN
    assert "sıfır olarak sayılmaz" in s["genel_gerekce"]


def test_sentez_genel_puan_olculen_eksenlerin_ortalamasidir():
    s = sentezle(tam_sirket(), risksiz_faiz=0.04)
    olculen = [e["puan"] for e in s["eksenler"] if e["durum"] == OLCULDU]
    assert len(olculen) >= ASGARI_EKSEN
    assert s["genel_puan"] == pytest.approx(round(sum(olculen) / len(olculen), 1))


def test_sentez_temettu_ekseni_yayimlanmamis_olarak_etiketlenir():
    s = sentezle(tam_sirket(), risksiz_faiz=0.04)
    temettu = [e for e in s["eksenler"] if e["anahtar"] == "temettu"][0]
    assert temettu["yayimlanmis"] is False
    diger = [e for e in s["eksenler"] if e["anahtar"] != "temettu"]
    assert all(e["yayimlanmis"] for e in diger)


def _canli_yasak_kelime_denetcisi():
    """Yasak kelime listesini KOPYALAMAK yerine projenin CANLI listesini
    yukler (maa/src/constitution.py). Anayasa Madde 1.3 listenin
    genisletilebilecegini soyluyor; kopya bir liste zamanla ayrisir ve test
    gercek sozlesmeyi olcmez hale gelirdi.

    Ilk denememde listeyi elle yazip DUZ ALT DIZE ile aramistim; "al " deseni
    "finansal" kelimesinin sonuna takilip YANLIS POZITIF uretti. Projenin
    kendi denetcisi bu hatayi coktan cozmus: kelime siniri (\b) kullaniyor.
    """
    import importlib.util
    yol = _anayasa_yolu()
    if yol is None:
        return None
    spec = importlib.util.spec_from_file_location("_anayasa", yol)
    modul = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(modul)
    except Exception:
        return None
    return getattr(modul, "check_banned_words", None)


def test_sentez_ciktisinda_yasak_dil_yok():
    """Anayasa Madde 1.3: emir/duygusal piyasa dili kullanilamaz."""
    denetle = _canli_yasak_kelime_denetcisi()
    if denetle is None:
        pytest.skip("maa/src/constitution.py okunamadi; canli yasak liste yok")
    s = sentezle(tam_sirket(), risksiz_faiz=0.04)
    metin = " ".join([s["genel_gerekce"], s["ticker"]] +
                     [f"{e['ad']} {e['aciklama']} {e['gerekce']} {e['kaynak']}"
                      for e in s["eksenler"]])
    ihlal = denetle(metin)
    assert ihlal == [], f"yasak dil bulundu: {ihlal}"


def test_yasak_dil_denetcisi_GERCEKTEN_calisiyor():
    """Yukaridaki testin sessizce her seyi gecirmedigini kanitlar: bilerek
    yasakli bir kelime iceren metin denetciden GECMEMELI."""
    denetle = _canli_yasak_kelime_denetcisi()
    if denetle is None:
        pytest.skip("canli yasak liste yok")
    assert denetle("Bu hisseyi al") != [], "denetci yasakli kelimeyi kacirdi"
    assert denetle("finansal saglik gostergesi") == [], \
        "denetci 'finansal' icindeki 'al' hecesine takiliyor (yanlis pozitif)"


# ==================== MUTASYON BOSLUKLARINI KAPATAN SINIR TESTLERI ==========
def test_piotroski_roa_DEGISMEDIYSE_kriter_saglanmaz():
    """MUTASYON M6: 'roa_artti: roa_t > roa_t1' -> '>=' mutasyonu hayatta
    kalmisti; fixture'da ROA kesin artiyordu, esitlik sinirini hicbir test
    olcmuyordu. Piotroski'de kriter ARTIS ister; degismemek artis degildir."""
    s = piotroski_sirketi()
    # ROA_t = NI_t/TA_{t-1} = 120/900; ROA_{t-1} = NI_{t-1}/TA_{t-2}
    # esitlemek icin: NI_{t-1} = (120/900)*800 = 106.666...
    s.donemler[1].gelir["Net Income"] = (120.0 / 900.0) * 800.0
    o = piotroski_f(s)
    assert o.ayrinti["roa_artti"] is False, "ROA degismemisken 'artti' sayildi"
    assert o.deger == 8.0


def test_piotroski_kaldirac_DEGISMEDIYSE_kriter_saglanmaz():
    s = piotroski_sirketi()
    # kaldirac_t = LTD_t/TA_t = 80/1000 = 0.08 -> t-1'i de 0.08 yap: 900*0.08=72
    s.donemler[1].bilanco["Long Term Debt"] = 72.0
    assert piotroski_f(s).ayrinti["kaldirac_azaldi"] is False


def test_temettu_odemeyende_deger_None_KALIR():
    """MUTASYON M9: temettu odemeyen sirkete 0 puan yazan bir degisiklik
    yakalanmali. 0 = 'temettusu var ama surdurulemez'; None = 'temettu yok'."""
    s = Sirket("TEST", [Donem("2026", gelir={"Net Income": 100.0},
                              nakit={"Free Cash Flow": 100.0})], piyasa={})
    o = temettu_dayanikligi(s)
    assert o.deger is None, "temettu odemeyene sayisal puan verilemez"
    assert o.durum == UYGULANAMAZ
    assert o.durum != OLCULDU


def test_sentez_TAM_IKI_eksende_genel_puan_URETMEZ():
    """MUTASYON M12: ASGARI_EKSEN 3->1 mutasyonu hayatta kalmisti, cunku tek
    testte SIFIR eksen olculuyordu. Burada tam IKI eksen olculuyor: esik
    dusurulurse bu test duser."""
    b = {"Total Assets": 1000.0, "Working Capital": 200.0, "Retained Earnings": 300.0,
         "Total Liabilities Net Minority Interest": 400.0, "Receivables": 100.0,
         "Current Assets": 400.0, "Net PPE": 300.0, "Current Liabilities": 200.0,
         "Long Term Debt": 100.0}
    g = {"EBIT": 150.0, "Total Revenue": 900.0, "Cost Of Revenue": 500.0,
         "Selling General And Administration": 100.0, "Net Income": 120.0}
    n = {"Depreciation And Amortization": 50.0, "Operating Cash Flow": 200.0}
    s = Sirket("IKI", [Donem("2026", bilanco=dict(b), gelir=dict(g), nakit=dict(n)),
                       Donem("2025", bilanco=dict(b), gelir=dict(g), nakit=dict(n))],
               piyasa={"piyasa_degeri": 2000.0})  # beta/fiyat yok -> DCF olculemez
    c = sentezle(s, risksiz_faiz=None)
    olculen = [e["anahtar"] for e in c["eksenler"] if e["durum"] == OLCULDU]
    assert olculen == ["finansal_saglik", "kazanc_kalitesi"], olculen
    assert c["olculebilen_eksen"] == 2
    assert c["genel_puan"] is None, "2 eksenle genel puan uretilmemeli"


def test_sentez_TAM_UC_eksende_genel_puan_URETILIR():
    """Esigin dogru yerde oldugunu iki yonlu kanitlar: 2'de uretmez, 3'te uretir."""
    p = piotroski_sirketi()   # 3 donem -> temel_guc olculur
    for d in (p.donemler[0], p.donemler[1]):
        d.bilanco.update({"Receivables": 100.0, "Net PPE": 300.0})
        d.gelir.update({"Cost Of Revenue": 500.0,
                        "Selling General And Administration": 100.0})
        d.nakit.setdefault("Operating Cash Flow", 200.0)
        d.nakit["Depreciation And Amortization"] = 50.0
    p.donemler[0].bilanco.update({"Working Capital": 200.0, "Retained Earnings": 300.0,
                                  "Total Liabilities Net Minority Interest": 400.0})
    p.donemler[0].gelir["EBIT"] = 150.0
    p.piyasa = {"piyasa_degeri": 2000.0}
    c = sentezle(p, risksiz_faiz=None)
    assert c["olculebilen_eksen"] == 3
    assert c["genel_puan"] is not None


def test_dcf_duyarlilik_bandi_bildirilir():
    """Bu eksen varsayima en duyarli olandir; tek sayi sunmak hak edilmemis
    kesinlik olurdu. Buyume +-5 puan oynatildiginda icsel deger de degismeli."""
    o = dcf_icsel_fiyat_orani(dcf_sirketi(), risksiz_faiz=0.04)
    band = o.ayrinti["duyarlilik"]
    assert set(band) == {"dusuk", "yuksek"}
    assert band["dusuk"]["icsel_deger"] < o.ayrinti["icsel_deger"] < band["yuksek"]["icsel_deger"]
    assert band["yuksek"]["buyume"] > band["dusuk"]["buyume"]


def test_dcf_buyume_kirpma_sinirlari_asilmaz():
    """Duyarlilik bandi da [-%5, +%15] kirpmasina uymali."""
    o = dcf_icsel_fiyat_orani(dcf_sirketi(), risksiz_faiz=0.04)
    for k in ("dusuk", "yuksek"):
        g = o.ayrinti["duyarlilik"][k]["buyume"]
        assert -0.05 <= g <= 0.15, f"{k} buyume kirpma disinda: {g}"
