"""Servis sozlesmesi: yasal uyari metni MAA ile AYNI kalmali."""
import os, sys, re, hashlib, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest


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


def _maa_uyarisi():
    yol = _anayasa_yolu()
    if yol is None:
        return None
    metin = open(yol, encoding="utf-8").read()
    m = re.search(r"LEGAL_DISCLAIMER = \((.*?)\n\)", metin, re.S)
    if not m:
        return None
    return "".join(re.findall(r'"([^"]*)"', m.group(1)))


#: Yasal uyari metnini tasiyan KUTSAL OLMAYAN servis kopyalari.
KUTSAL_OLMAYAN_KOPYALAR = [
    "skor-sentezi-service",
    "stres-testi-service",
    "portfoy-service",
]


def _servis_ana_yolu(servis):
    """<servis>/src/main.py'yi _anayasa_yolu() ile AYNI cok-adayli desenle
    bulur; bulunamazsa None doner. Cagiran taraf bunu ATLAMA degil
    BASARISIZLIK olarak isler."""
    adaylar = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), servis, "src", "main.py"),
        "/repo/%s/src/main.py" % servis,
        os.path.join(os.environ.get("DEPO_KOK", ""), servis, "src", "main.py"),
    ]
    for y in adaylar:
        if y and os.path.exists(y):
            return y
    return None


def _dosyadan_uyari(yol):
    """YASAL_UYARI metnini SALT-OKUNUR cikarir. Servisi ice AKTARMAZ: ice
    aktarma, denetlenen dosyanin calisma zamani bagimliliklarini surukler ve
    metin esitligi sorusunu ilgisiz bir kurulum sorusuna cevirir."""
    metin = open(yol, encoding="utf-8").read()
    m = re.search(r"YASAL_UYARI = \((.*?)\n\)", metin, re.S)
    if not m:
        return None
    return "".join(re.findall(r'"([^"]*)"', m.group(1)))


@pytest.mark.parametrize("servis", KUTSAL_OLMAYAN_KOPYALAR)
def test_yasal_uyari_kutsal_olmayan_kopyalarda_ayni(servis):
    """Yasal uyari metninin KUTSAL OLMAYAN kopyalari, kaynaktan (maa/src/
    constitution.py) BIREBIR ayrismasin diye kilitlenir.

    KAPSAM DISI -- maa/src/main.py: o dosya KUTSAL'dir ve bu calismada ona
    erisim (yazma VE okuma) yasaktir, bu yuzden testin kapsamina bilerek
    ALINMAMISTIR. O kopyanin denetlenmesi AYRI bir karardir (bkz. AB-018).
    Bu testin YESIL olmasi, kutsal kopyanin dogrulandigi anlamina GELMEZ.

    Bu bir REGRESYON KILIDIDIR: yazildigi anda metinler zaten esittir, bu
    yuzden ilk kosuda GECER. Kapatilan kusur bir metin ayrismasi degil,
    ayrismayi yakalayacak makine garantisinin YOKLUGUDUR."""
    maa = _maa_uyarisi()
    assert maa is not None, \
        "maa/src/constitution.py okunamadi -- bu test ATLANMAZ, BASARISIZ olur"
    yol = _servis_ana_yolu(servis)
    assert yol is not None, \
        "%s/src/main.py bulunamadi -- bu test ATLANMAZ, BASARISIZ olur" % servis
    uyari = _dosyadan_uyari(yol)
    assert uyari is not None, "%s icinde YASAL_UYARI tanimi bulunamadi" % yol
    assert uyari == maa, "yasal uyari metni kaynaktan ayrismis: %s" % yol


def test_yasal_uyari_maa_ile_ayni():
    """Metin servis bagimsizligi icin kopyalandi; SESSIZCE AYRISMASIN diye
    burada denetleniyor. Anayasa Madde 1.4 bu metni zorunlu kiliyor."""
    from src.main import YASAL_UYARI
    maa = _maa_uyarisi()
    if maa is None:
        pytest.skip("maa/src/constitution.py okunamadi")
    assert YASAL_UYARI == maa, "yasal uyari metni MAA'dakiyle ayrismis"


def test_saglik_ucu_eksen_sayisini_bildirir():
    from src.main import health
    h = health()
    assert h["eksen_sayisi"] == 5 and h["asgari_eksen"] == 3


#: Eksen KIMLIK alanlarinin (anahtar+kaynak+yayimlanmis) kilit hash'i.
#: Yalnizca kimlik alanlari kilitlenir: 'ad' ve 'aciklama' redaksiyon
#: metinleridir, degismeleri metodoloji degisikligi DEGILDIR.
EKSEN_TANIM_KILIDI = \
    "0514461f035d9ee3427b719da265a56c7f91955146fe1213d5d1492c7f25b2c8"


def _eksen_tanim_hash(tanimlar):
    govde = "\n".join("%s|%s|%s" % (t["anahtar"], t["kaynak"], t["yayimlanmis"])
                      for t in tanimlar)
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()


def _eksenler_ucunun_govdesi():
    """main.py'deki /eksenler ucunun govdesini SALT-OKUNUR cikarir.

    _dosyadan_uyari() ile AYNI gerekce: modulu ice aktarmak servisin
    calisma zamani bagimliliklarini (fastapi) surukler ve sozlesme
    sorusunu ilgisiz bir kurulum sorusuna cevirir."""
    yol = _servis_ana_yolu("skor-sentezi-service")
    assert yol is not None, \
        "skor-sentezi-service/src/main.py bulunamadi -- ATLANMAZ, BASARISIZ"
    metin = open(yol, encoding="utf-8").read()
    m = re.search(r'@app\.get\("/eksenler"\)\ndef eksenler\(\):(.*?)\n@app\.',
                  metin, re.S)
    assert m is not None, "/eksenler ucu %s icinde bulunamadi" % yol
    return m.group(1)


def test_eksenler_ucu_surum_ve_son_guncelleme_bildirir():
    """Yayimlanmis metodoloji yuzeyi KENDI YASINI soylemeli.

    Surum ve son guncelleme damgasi olmadan kullanici, yayimlanan eksen
    tanimlari ile yasayan urun arasindaki zaman araligini DENETLEYEMEZ."""
    from src.sentez import METODOLOJI_SURUMU, METODOLOJI_SON_GUNCELLEME
    assert re.fullmatch(r"\d+\.\d+\.\d+", METODOLOJI_SURUMU), \
        "METODOLOJI_SURUMU BUYUK.KUCUK.YAMA olmali: %r" % (METODOLOJI_SURUMU,)
    # Bicim degil GECERLILIK: "2026-13-45" regex'i gecer, tarih degildir.
    datetime.date.fromisoformat(METODOLOJI_SON_GUNCELLEME)

    govde = _eksenler_ucunun_govdesi()
    # Yalnizca ALAN ADININ metinde gecmesi YETMEZ (bulundu: bagimsiz
    # denetci, 2026-09-25): govde alani SABIT-KODLU bir deger ile
    # doldurup (orn. "9.9.9") testi hala gecirebilirdi - bu, AB-044'un
    # tarif ettigi 'yanlis etiket' kusurunun aynisidir. Alanin GERCEKTEN
    # ithal edilen sabite BAGLI oldugu, isim BAZINDA dogrulanir.
    assert re.search(r'"metodoloji_surumu"\s*:\s*METODOLOJI_SURUMU\b', govde), \
        ("/eksenler govdesi 'metodoloji_surumu' alanini METODOLOJI_SURUMU "
         "sabitine BAGLAMIYOR (sabit-kodlu/uydurma bir deger olabilir)")
    assert re.search(r'"son_guncelleme"\s*:\s*METODOLOJI_SON_GUNCELLEME\b', govde), \
        ("/eksenler govdesi 'son_guncelleme' alanini METODOLOJI_SON_GUNCELLEME "
         "sabitine BAGLAMIYOR (sabit-kodlu/uydurma bir deger olabilir)")


def test_eksen_tanimlari_hash_ile_kilitli():
    """son_guncelleme ELLE tutulan bir sabittir; tek basina BAYATLAR.

    Bu kilit, eksen kimlik alanlari degistiginde testi kirar ve boylece
    METODOLOJI_SURUMU ile METODOLOJI_SON_GUNCELLEME'nin birlikte
    guncellenmesini ZORUNLU kilar. Bir 'yanlis etiket' kusurunu onler."""
    from src.sentez import EKSEN_TANIMLARI
    assert _eksen_tanim_hash(EKSEN_TANIMLARI) == EKSEN_TANIM_KILIDI, (
        "Eksen tanimlari degismis. METODOLOJI_SURUMU'nu yukseltin, "
        "METODOLOJI_SON_GUNCELLEME'yi degisikligin commit tarihine "
        "gore guncelleyin, sonra bu kilidi yenileyin.")
