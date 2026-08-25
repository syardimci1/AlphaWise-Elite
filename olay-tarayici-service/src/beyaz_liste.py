"""
KAYNAK BEYAZ LISTESI — bu servisin YASAL SINIRI, kod seviyesinde.

=======================================================================
NEDEN IKI KATMAN (24.08.2026'da OLCULEREK bulundu)
=======================================================================
Ilk tasarim "resmi bir alan adiysa guvenilirdir" varsayimina dayaniyordu.
Bu YANLIS cikti. Nasdaq'in KENDI RSS akisi (www.nasdaq.com, resmi bir
borsa) olculdugunde icerigin Nasdaq'a ait olmadigi goruldu: dc:creator
dagilimi RTTNews (8), The Motley Fool (5), Barchart (2) — yani ucuncu
taraf sendikasyonu. Resmi bir HOST, birincil bir KAYNAK anlamina gelmiyor.

Bu yuzden iki bagimsiz katman var:

  KATMAN 1 — URL IZNI (ag cagrisindan ONCE):
      Istek atilacak adres, asagidaki dondurulmus listedeki bir kayitla
      host VE yol oneki bakimindan eslesmek ZORUNDA. Eslesmezse ag
      cagrisi HIC YAPILMAZ; KaynakReddedildi yukselir.

  KATMAN 2 — BIRINCIL KAYNAK DOGRULAMASI:
      Eslesen kaydin `kendi_icerigini_yayinlar` alani True olmak ZORUNDA.
      Nasdaq gibi bir kaynak ileride listeye eklenmek istense bile bu
      alan False olacagi icin gecemez.

=======================================================================
LISTEYE GIRME OLCUTU
=======================================================================
Bir kaynak ancak su UCUNU birden saglarsa eklenebilir:
  1. Icerigi kendi ureten resmi bir duzenleyici ya da kamu kurumu olmali
     (ya da sirketin KENDI yatirimci iliskileri kanali).
  2. Ticari kullanimi acikca serbest olmali.
  3. robots.txt otomatik erisime izin vermeli.

Su an listedeki kaynaklarin HEPSI ABD federal kamu malidir
(17 U.S.C. 105 — federal hukumet eserleri telif korumasi disindadir),
yani ticari kullanim serbesttir.

=======================================================================
BILEREK DISARIDA BIRAKILANLAR (ve nedenleri — olculdu)
=======================================================================
  PR Newswire     : ToS "solely for your personal, noncommercial use";
                    ayrica robot/spider ile "data mine" ve "electronic
                    redistribution or database storage" acikca yasak.
                    AlphaWise ticari + otomatik -> KULLANILAMAZ.
  Reuters         : halka acik RSS kapali (HTTP 401).
  AP              : HTTP 404.
  Bloomberg       : akis calisiyor (HTTP 200) ama ticari kullanim sartlari
                    DOGRULANAMADI -> kullanici karari cikana kadar disarida.
  GlobeNewswire   : /RssFeed/ robots'ta yasak degil ama ToS sayfasi
                    bulunamadi (404) -> DOGRULANMAMIS, disarida.
  Nasdaq RSS      : icerigi kendi degil (yukariya bakiniz).
  apps.bea.gov    : icerigi GERCEKTEN BEA (dogrulandi, 47 oge) AMA
                    robots.txt'i "User-agent: *  Disallow: /" diyor — tum
                    host otomatik erisime kapali. www.bea.gov/rss/rss.xml
                    buraya 301 ile yonlendirdigi icin O ADRES DE
                    kullanilamaz; onun yerine yonlendirmeyen
                    www.bea.gov/news/rss kullaniliyor.
  Google News     : belgelenmemis uc, Google ToS otomatik erisimi kisitlar.
  Yahoo/SeekingAlpha/Benzinga/MarketWatch/CNBC : ikincil/yorum icerigi.
  SEC /cgi-bin/browse-edgar (getcurrent RSS) : SEC'in KENDI robots.txt'i
                    satir 85'te "Disallow: /cgi-bin" diyor. SEC'in FAQ'su
                    bu ucu onerse de, robots.txt baglayici kabul edildi.
                    Kaybimiz YOK: olculdu, RSS'teki 10 dosyalamanin 10'u
                    da data.sec.gov'da AYNI zaman damgasiyla mevcuttu.

DEDIKODU/SOYLENTI KAYNAKLARI hicbir kosulda eklenemez: reddit,
wallstreetbets, stocktwits, twitter/X, discord, telegram, forum, "whisper",
"rumor", "leak", "unusual options activity", paywall asma.
"""
from dataclasses import dataclass
from typing import Tuple
from urllib.parse import urlparse


class KaynakReddedildi(Exception):
    """Beyaz listede olmayan ya da birincil olmayan bir kaynaga erisim denendi."""


@dataclass(frozen=True)
class Kaynak:
    kimlik: str
    host: str
    yol_onekleri: Tuple[str, ...]
    tur: str                      # duzenleyici | kamu_kurumu
    kurum: str
    lisans_dayanagi: str
    kendi_icerigini_yayinlar: bool
    robots_notu: str


# Dondurulmus: calisma aninda degistirilemez (tuple + frozen dataclass).
IZINLI_KAYNAKLAR: Tuple[Kaynak, ...] = (
    Kaynak(
        kimlik="sec_submissions",
        host="data.sec.gov",
        yol_onekleri=("/submissions/",),
        tur="duzenleyici",
        kurum="U.S. Securities and Exchange Commission",
        lisans_dayanagi="ABD federal kamu mali (17 U.S.C. 105)",
        kendi_icerigini_yayinlar=True,
        robots_notu="data.sec.gov'da robots.txt yok (HTTP 404); SEC bu ucu "
                    "programatik erisim icin belgeliyor.",
    ),
    Kaynak(
        kimlik="sec_arsiv",
        host="www.sec.gov",
        yol_onekleri=("/Archives/edgar/data/", "/Archives/edgar/daily-index/",
                      "/Archives/edgar/full-index/"),
        tur="duzenleyici",
        kurum="U.S. Securities and Exchange Commission",
        lisans_dayanagi="ABD federal kamu mali (17 U.S.C. 105)",
        kendi_icerigini_yayinlar=True,
        robots_notu="robots.txt satir 81: 'Allow: /Archives/edgar/data'. "
                    "daily-index ve full-index icin yasak kural yok.",
    ),
    Kaynak(
        kimlik="fed_basin",
        host="www.federalreserve.gov",
        yol_onekleri=("/feeds/",),
        tur="kamu_kurumu",
        kurum="Board of Governors of the Federal Reserve System",
        lisans_dayanagi="ABD federal kamu mali (17 U.S.C. 105)",
        kendi_icerigini_yayinlar=True,
        robots_notu="robots.txt'te User-agent:* icin Disallow YOK.",
    ),
    Kaynak(
        kimlik="bls_yayin",
        host="www.bls.gov",
        yol_onekleri=("/feed/",),
        tur="kamu_kurumu",
        kurum="Bureau of Labor Statistics",
        lisans_dayanagi="ABD federal kamu mali (17 U.S.C. 105)",
        kendi_icerigini_yayinlar=True,
        robots_notu="/feed/ icin yasak kural yok. DIKKAT: tarayici "
                    "User-Agent'i ile HTTP 403 doner; bildirimli UA sart.",
    ),
    Kaynak(
        kimlik="bea_yayin",
        host="www.bea.gov",
        yol_onekleri=("/rss/", "/news/"),
        tur="kamu_kurumu",
        kurum="Bureau of Economic Analysis",
        lisans_dayanagi="ABD federal kamu mali (17 U.S.C. 105)",
        kendi_icerigini_yayinlar=True,
        robots_notu="/rss/ ve /news/ icin yasak kural yok.",
    ),
)

_KIMLIGE_GORE = {k.kimlik: k for k in IZINLI_KAYNAKLAR}


def kaynak_bul(url: str):
    """URL'e karsilik gelen izinli kaydi dondurur; yoksa None."""
    p = urlparse(url)
    if p.scheme != "https":
        return None            # duz HTTP kabul edilmez
    for k in IZINLI_KAYNAKLAR:
        if p.hostname == k.host and any(p.path.startswith(o) for o in k.yol_onekleri):
            return k
    return None


def url_dogrula(url: str) -> Kaynak:
    """
    KATMAN 1 + KATMAN 2. Gecemezse KaynakReddedildi yukselir.

    Bu fonksiyon, ag cagrisi yapan TEK gecis noktasi olan
    kaynaklar.guvenli_get() tarafindan cagrilir. Baska hicbir yerde
    dogrudan HTTP cagrisi yapilmaz; test_beyaz_liste.py bunu kaynak
    kodu tarayarak kilitler.
    """
    if not isinstance(url, str) or not url:
        raise KaynakReddedildi("Bos ya da gecersiz adres")

    k = kaynak_bul(url)
    if k is None:
        # Sebep disariya AYRINTILI verilmez; log'a yazilir.
        raise KaynakReddedildi(
            f"KATMAN 1 RED: adres beyaz listede yok ({urlparse(url).hostname})"
        )
    if not k.kendi_icerigini_yayinlar:
        raise KaynakReddedildi(
            f"KATMAN 2 RED: '{k.kimlik}' kendi icerigini yayinlamiyor "
            f"(ucuncu taraf sendikasyonu)"
        )
    return k


def liste_ozeti() -> list:
    """Arayuze/rapora gosterilecek ozet — sir icermez."""
    return [
        {
            "kimlik": k.kimlik,
            "kurum": k.kurum,
            "host": k.host,
            "yol_onekleri": list(k.yol_onekleri),
            "tur": k.tur,
            "lisans_dayanagi": k.lisans_dayanagi,
            "birincil_kaynak": k.kendi_icerigini_yayinlar,
        }
        for k in IZINLI_KAYNAKLAR
    ]
