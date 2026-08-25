"""
TEK AG GECIS NOKTASI + kaynak okuyuculari.

Bu modulun disinda HICBIR yerde HTTP cagrisi yapilmaz. Kural test ile
kilitlenmistir (tests/test_beyaz_liste.py, "gecis noktasi disinda ham
HTTP yok" testi kaynak kodu tarar).

SEC HIZ SINIRI: SEC'in politikasi saniyede 10 istek ve sinir IP BAZLIDIR
("regardless of the number of machines"). Bu depoda zaten IP bazli, Redis
destekli bir sayac var (sec-edgar-13f-service/src/rate_limiter.py); ayni
ilke burada da uygulanir ve AYNI Redis anahtarini kullanir, boylece iki
servis birbirinin payini yemez.

USER-AGENT: SEC ve BLS bildirimli bir User-Agent bekliyor. BLS bunu
zorunlu tutuyor: tarayici UA'si ile HTTP 403, bildirimli UA ile HTTP 200
(24.08.2026'da olculdu).
"""
import logging
import os
import time

import httpx

from .beyaz_liste import KaynakReddedildi, url_dogrula

logger = logging.getLogger("olay-tarayici.kaynaklar")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# SEC'in kurali: iletisim bilgisi iceren bildirimli UA.
USER_AGENT = os.getenv(
    "KAYNAK_USER_AGENT",
    "AlphaWise Event Scanner selcukyardimci@proton.me",
)
ZAMAN_ASIMI = float(os.getenv("KAYNAK_ZAMAN_ASIMI", "20"))

# SEC 10 istek/sn; muhafazakar davranip 5'te tutuyoruz (diger servisler de
# ayni IP'den cikiyor).
SEC_SANIYEDE = float(os.getenv("SEC_SANIYEDE", "5"))
_SEC_ANAHTAR = "ratelimit:sec-edgar"


def _redis():
    try:
        import redis
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
            socket_connect_timeout=3, socket_timeout=3,
        )
        r.ping()
        return r
    except Exception:
        return None


_R = _redis()
_son_yerel = 0.0


def _sec_bekle():
    """IP bazli kaba jeton kovasi. Redis yoksa surec-ici geri duser."""
    global _son_yerel
    araluk = 1.0 / SEC_SANIYEDE
    if _R is not None:
        try:
            simdi = time.time()
            son = float(_R.get(_SEC_ANAHTAR) or 0)
            bekle = (son + araluk) - simdi
            if bekle > 0:
                time.sleep(min(bekle, 2.0))
                simdi = time.time()
            _R.set(_SEC_ANAHTAR, simdi, ex=60)
            return
        except Exception:
            pass
    gecen = time.time() - _son_yerel
    if gecen < araluk:
        time.sleep(araluk - gecen)
    _son_yerel = time.time()


def guvenli_get(url: str, kabul: str = "application/json") -> httpx.Response:
    """
    TEK ag gecis noktasi.

    Once beyaz liste (iki katman) dogrulanir; GECMEZSE AG CAGRISI
    YAPILMADAN KaynakReddedildi yukselir. Bu sira bilinclidir: reddedilen
    bir adrese tek bir paket bile gitmez.
    """
    # YONLENDIRME BIR ATLATMA VEKTORUDUR (25.08.2026'da CANLI ORNEK BULUNDU):
    # https://www.bea.gov/rss/rss.xml  --301-->  https://apps.bea.gov/...
    # ve apps.bea.gov'un robots.txt'i "Disallow: /" diyor. httpx'e
    # follow_redirects=True verilseydi istek, beyaz liste HIC calismadan
    # listede olmayan ve robots'ta yasak bir hosta giderdi.
    # Bu yuzden yonlendirmeler ELDE, HER ADIMDA yeniden dogrulanarak
    # izlenir ve adim sayisi sinirlidir.
    kalan_atlama = 3
    su_anki = url
    while True:
        kaynak = url_dogrula(su_anki)      # <-- yasal sinir HER ADIMDA zorlanir
        if kaynak.host.endswith("sec.gov"):
            _sec_bekle()
        with httpx.Client(timeout=ZAMAN_ASIMI, follow_redirects=False) as c:
            y = c.get(su_anki, headers={"User-Agent": USER_AGENT, "Accept": kabul})
        if y.status_code in (301, 302, 303, 307, 308):
            hedef = y.headers.get("location")
            if not hedef:
                break
            hedef = str(httpx.URL(su_anki).join(hedef))
            if kalan_atlama <= 0:
                raise KaynakReddedildi("Cok fazla yonlendirme")
            logger.info("yonlendirme: %s -> %s (yeniden dogrulanacak)",
                        kaynak.kimlik, hedef)
            kalan_atlama -= 1
            su_anki = hedef
            continue
        break
    logger.info("kaynak=%s HTTP=%s bayt=%s", kaynak.kimlik, y.status_code,
                len(y.content))
    return y


# ---------------------------------------------------------------------------
# SEC
# ---------------------------------------------------------------------------
def sec_sirket_dosyalamalari(cik: int) -> dict:
    """
    data.sec.gov resmi yapili API'si.

    NEDEN getcurrent RSS DEGIL: SEC'in kendi robots.txt'i /cgi-bin'i
    yasakliyor. Kaybimiz olmadigi OLCULDU: RSS'teki 10 dosyalamanin
    10'u da burada, AYNI zaman damgasiyla mevcuttu.
    """
    u = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
    y = guvenli_get(u)
    y.raise_for_status()
    return y.json()


def sec_gunluk_indeks(tarih: str) -> str:
    """/Archives/edgar/daily-index — robots'ta yasak kurali yok."""
    yil = tarih[:4]
    ceyrek = (int(tarih[5:7]) - 1) // 3 + 1
    ymd = tarih.replace("-", "")
    u = (f"https://www.sec.gov/Archives/edgar/daily-index/"
         f"{yil}/QTR{ceyrek}/form.{ymd}.idx")
    y = guvenli_get(u, kabul="text/plain")
    y.raise_for_status()
    return y.text


# ---------------------------------------------------------------------------
# Kamu kurumu yayin akislari (RSS/Atom)
# ---------------------------------------------------------------------------
KURUM_AKISLARI = {
    "fed_basin": "https://www.federalreserve.gov/feeds/press_all.xml",
    "bls_yayin": "https://www.bls.gov/feed/bls_latest.rss",
    # BEA ADRESI IKI KEZ DUZELTILDI (24-25.08.2026, ikisi de OLCUMLE):
    #   1) /rss.xml      -> HTTP 404 (35 KB'lik "sayfa bulunamadi" HTML'i;
    #      sessizce bos akis gibi gorunurdu). Pozitif kontrol testi yakaladi.
    #   2) /rss/rss.xml  -> HTTP 301, hedef apps.bea.gov. Icerik GERCEKTEN
    #      BEA (47 oge, dogrulandi) AMA apps.bea.gov/robots.txt
    #      "User-agent: *  Disallow: /" diyor — TUM host otomatik erisime
    #      kapali. Bu yuzden apps.bea.gov beyaz listeye EKLENMEDI.
    #   3) /news/rss      -> HTTP 200, yonlendirme YOK, application/rss+xml,
    #      11 oge (GSYH, Kisisel Gelir, Dis Ticaret). www.bea.gov/robots.txt
    #      /news/ yolunu ENGELLEMIYOR. Kullanilan adres budur.
    "bea_yayin": "https://www.bea.gov/news/rss",
}


def kurum_akisi(kimlik: str) -> str:
    if kimlik not in KURUM_AKISLARI:
        raise KaynakReddedildi(f"Tanimsiz akis: {kimlik}")
    y = guvenli_get(KURUM_AKISLARI[kimlik], kabul="application/rss+xml, application/xml, text/xml")
    y.raise_for_status()
    return y.text
