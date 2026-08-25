"""
YASAL SINIR TESTLERI — bu dosya, whitelist'in gercekten zorlayici
oldugunu KANITLAR. Gecmezse servis yayina alinamaz.
"""
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.beyaz_liste import (  # noqa: E402
    IZINLI_KAYNAKLAR, KaynakReddedildi, kaynak_bul, url_dogrula,
)

# --- NEGATIF KONTROL: bunlarin HICBIRI kabul edilmemeli ---
YASAK_ADRESLER = [
    # sosyal medya / forum / dedikodu
    "https://www.reddit.com/r/wallstreetbets/new.json",
    "https://old.reddit.com/r/stocks/.rss",
    "https://api.stocktwits.com/api/2/streams/symbol/AAPL.json",
    "https://x.com/i/api/graphql/tweets",
    "https://twitter.com/elonmusk",
    "https://discord.com/api/v9/channels/123/messages",
    "https://t.me/s/some_leak_channel",
    "https://boards.4chan.org/biz/",
    # sizinti/soylenti siteleri
    "https://www.insidermonkey.com/blog/feed/",
    "https://unusualwhales.com/api/flow",
    "https://sizinti-forum.example/leaks.rss",
    # ikincil/yorum
    "https://seekingalpha.com/feed.xml",
    "https://www.benzinga.com/feed",
    "https://finance.yahoo.com/news/rssindex",
    # ticari kullanima kapali
    "https://www.prnewswire.com/rss/news-releases-list.rss",
    # sartlari dogrulanmamis
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/x",
    # icerigi kendi olmayan resmi host
    "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
    # SEC ama robots'ta YASAK yol
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom",
    # dogru host, YANLIS yol
    "https://www.sec.gov/litigation/admin.htm",
    "https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/CY2025Q1I.json",
    # duz HTTP (sifresiz)
    "http://data.sec.gov/submissions/CIK0000320193.json",
    # host taklidi
    "https://data.sec.gov.saldirgan.example/submissions/CIK0000320193.json",
    "https://evil-www.sec.gov/Archives/edgar/data/1/x.htm",
    # bos/bozuk
    "",
    "javascript:alert(1)",
    "file:///etc/passwd",
]

# --- POZITIF KONTROL: bunlar kabul EDILMELI ---
IZINLI_ADRESLER = [
    "https://data.sec.gov/submissions/CIK0000320193.json",
    "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000069/nvda-20260817.htm",
    "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR3/form.20260821.idx",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://www.bls.gov/feed/bls_latest.rss",
    "https://www.bea.gov/rss/rss.xml",
]


@pytest.mark.parametrize("url", YASAK_ADRESLER)
def test_yasak_adres_reddedilir(url):
    """NEGATIF KONTROL — listede olmayan hicbir adres gecemez."""
    with pytest.raises(KaynakReddedildi):
        url_dogrula(url)


@pytest.mark.parametrize("url", IZINLI_ADRESLER)
def test_izinli_adres_gecer(url):
    """POZITIF KONTROL — testin gercekten ayirt ettigini gosterir."""
    k = url_dogrula(url)
    assert k.kendi_icerigini_yayinlar is True


def test_ikinci_katman_birincil_olmayani_reddeder():
    """
    KATMAN 2: bir kaynak listeye eklense BILE, kendi icerigini
    yayinlamiyorsa gecemez. (Nasdaq senaryosu.)
    """
    import dataclasses

    from src import beyaz_liste as bl

    sahte = dataclasses.replace(
        IZINLI_KAYNAKLAR[0], kimlik="sahte_sendikasyon",
        host="sendikasyon.example", yol_onekleri=("/rss/",),
        kendi_icerigini_yayinlar=False,
    )
    orij = bl.IZINLI_KAYNAKLAR
    try:
        bl.IZINLI_KAYNAKLAR = orij + (sahte,)
        with pytest.raises(KaynakReddedildi) as e:
            bl.url_dogrula("https://sendikasyon.example/rss/x.xml")
        assert "KATMAN 2" in str(e.value)
    finally:
        bl.IZINLI_KAYNAKLAR = orij


def test_liste_dondurulmus():
    """Kayitlar calisma aninda degistirilemez."""
    import dataclasses

    assert isinstance(IZINLI_KAYNAKLAR, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        IZINLI_KAYNAKLAR[0].host = "saldirgan.example"


def test_tum_kayitlar_birincil():
    """Listede birincil olmayan bir kaynak BULUNMAMALI."""
    for k in IZINLI_KAYNAKLAR:
        assert k.kendi_icerigini_yayinlar is True, k.kimlik
        assert k.tur in ("duzenleyici", "kamu_kurumu"), k.kimlik


def test_gecis_noktasi_disinda_ham_http_yok():
    """
    KOD SEVIYESINDE ZORLAMA: beyaz listeyi atlamanin tek yolu, gecis
    noktasini (kaynaklar.guvenli_get) kullanmadan dogrudan HTTP cagirmak
    olurdu. Bu test kaynak kodu tarayarak bunu engeller.
    """
    kok = pathlib.Path(__file__).resolve().parents[1] / "src"
    desen = re.compile(
        r"\b(httpx\.(get|post|stream|Client)|requests\.(get|post)|"
        r"urlopen|aiohttp)\b"
    )
    izinli = {"kaynaklar.py", "bildirim.py"}   # gecis noktasi + whatsapp
    ihlal = []
    for f in kok.glob("*.py"):
        if f.name in izinli:
            continue
        for i, satir in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if desen.search(satir) and not satir.strip().startswith("#"):
                ihlal.append(f"{f.name}:{i}: {satir.strip()[:70]}")
    assert not ihlal, "Gecis noktasi disinda ham HTTP cagrisi:\n" + "\n".join(ihlal)


def test_gecis_noktasi_once_dogrular():
    """guvenli_get, ag cagrisindan ONCE url_dogrula cagirmali."""
    kok = pathlib.Path(__file__).resolve().parents[1] / "src"
    kod = (kok / "kaynaklar.py").read_text(encoding="utf-8")
    govde = kod.split("def guvenli_get", 1)[1]
    d = govde.find("url_dogrula(")
    a = govde.find("c.get(")
    assert d != -1 and a != -1, "beklenen cagrilar bulunamadi"
    assert d < a, "url_dogrula, ag cagrisindan SONRA cagriliyor"


def test_dedikodu_deseni_kaynakta_yok():
    """Kaynak kodda dedikodu kaynagi izi olmamali."""
    kok = pathlib.Path(__file__).resolve().parents[1] / "src"
    yasak = re.compile(
        r"(reddit|wallstreetbets|stocktwits|4chan|unusualwhales|"
        r"insidermonkey)\.(com|net|org)", re.I)
    for f in kok.glob("*.py"):
        m = yasak.search(f.read_text(encoding="utf-8"))
        assert not m, f"{f.name}: {m.group() if m else ''}"


def test_yonlendirme_listede_olmayan_hosta_gidemez(monkeypatch):
    """
    ATLATMA VEKTORU TESTI (25.08.2026'da CANLI ORNEKLE bulundu):
    www.bea.gov/rss/rss.xml -> 301 -> apps.bea.gov (robots: Disallow: /)

    guvenli_get, yonlendirmeleri elde izler ve HER ADIMDA url_dogrula
    cagirir. Listede olmayan bir hedefe yonlendirilirse KaynakReddedildi
    yukselmeli — ve o hedefe ISTEK ATILMAMALI.
    """
    import httpx

    from src import kaynaklar

    gidilen = []

    class SahteYanit:
        def __init__(self, kod, loc=None):
            self.status_code = kod
            self.headers = {"location": loc} if loc else {}
            self.content = b""

    class SahteIstemci:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, **k):
            gidilen.append(url)
            if url.startswith("https://www.bea.gov/"):
                return SahteYanit(301, "https://apps.bea.gov/rss/rss.xml")
            return SahteYanit(200)

    monkeypatch.setattr(httpx, "Client", SahteIstemci)
    monkeypatch.setattr(kaynaklar, "_sec_bekle", lambda: None)

    with pytest.raises(KaynakReddedildi):
        kaynaklar.guvenli_get("https://www.bea.gov/news/rss")

    assert gidilen == ["https://www.bea.gov/news/rss"], (
        "Listede olmayan yonlendirme hedefine istek ATILMAMALIYDI: %s" % gidilen
    )


def test_yonlendirme_sayisi_sinirli(monkeypatch):
    """Sonsuz yonlendirme dongusu servisi kilitleyemez."""
    import httpx

    from src import kaynaklar

    class SahteYanit:
        def __init__(self):
            self.status_code = 301
            # Ayni izinli host icinde donen bir dongu
            self.headers = {"location": "https://www.bea.gov/news/rss?x=1"}
            self.content = b""

    class SahteIstemci:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, **k): return SahteYanit()

    monkeypatch.setattr(httpx, "Client", SahteIstemci)
    monkeypatch.setattr(kaynaklar, "_sec_bekle", lambda: None)
    with pytest.raises(KaynakReddedildi) as e:
        kaynaklar.guvenli_get("https://www.bea.gov/news/rss")
    assert "yonlendirme" in str(e.value).lower()
