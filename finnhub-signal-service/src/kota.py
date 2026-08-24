"""
Finnhub DAKIKALIK kota bekcisi.

=======================================================================
NEDEN VAR (23.08.2026'da CANLI OLCULDU, varsayilmadi)
=======================================================================
Finnhub ucretsiz katmanin limiti anahtar basina DAKIKADA 60 istektir.
Bu, belgeden degil GERCEK yanit basligindan okundu:

    /quote            -> HTTP 200  x-ratelimit-limit: 60  remaining: 59
    /company-news     -> HTTP 200  x-ratelimit-limit: 60  remaining: 48
    /calendar/earnings-> HTTP 200  x-ratelimit-limit: 60  remaining: 47

Dikkat edilmesi gereken nokta: art arda yapilan bu uc olcumde "remaining"
59 -> 48 -> 47 diye DUSTU, oysa biz aradan yalnizca birer istek yaptik.
Aradaki farki BIZ tuketmedik: FINNHUB_API_KEY_1..4 havuzunu zaten
kullanan DORT servis var (saa, news-monitor, oanda, godmode-execution)
ve onlar ayni anda cagri yapiyor. Yani kota PAYLASILMIS ve AKTIF.

Bu, FMP'de yasanan tuzagin aynisidir: bekcisiz eklenen yeni bir tuketici,
kullanici-yuzu bir servisin payini sessizce yer. Oradaki cozumun (qlib ve
finrl-x'teki fmp_kota) dakikalik surumu burada uygulanir.

=======================================================================
BU BEKCININ NEYI GARANTI EDER / NEYI ETMEZ
=======================================================================
EDER : BU servisin dakikada belirlenen tavandan fazla Finnhub cagrisi
       yapmasini engeller. Yani dashboard karti, ne kadar yenilenirse
       yenilensin havuzu tek basina bosaltamaz.
ETMEZ: diger dort servisi sinirlamaz — onlarin kendi sayaci yok ve bu
       gorevde onlara DOKUNULMADI (mevcut servislere dokunma kurali).
       Dolayisiyla toplam tuketim hala onlarin davranisina baglidir.
       Bu bilincli ve belgelenmis bir sinirdir.

Redis'e ulasilamazsa FAIL-OPEN calisir (uyarir, durdurmaz): burada
kaybedilen para degil yalnizca hiz limitidir, ve 429 durumunda istemci
zaten anahtar rotasyonuna dusuyor. Ayni tercih fmp_kota'da da yapildi.
"""
import datetime
import os

# Havuzdaki her anahtarin dakikalik limiti (OLCULDU: 60).
ANAHTAR_BASINA_DAKIKA_LIMITI = 60

# BU servisin kendine ayirdigi pay. Varsayilan 15: dort mevcut tuketiciye
# anahtar basina 45 istek/dk birakir. Dashboard'in bir acilisi bu ucu
# ticker basina 1 kez cagirdigi icin 15 fazlasiyla yeterlidir.
DAKIKALIK_BUTCE = int(os.getenv("FINNHUB_DAKIKALIK_BUTCE", "15"))

ONEK = "finnhub:dk:"


def _dakika() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M")


def _redis():
    try:
        import redis

        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        r.ping()
        return r
    except Exception:
        return None


class DakikaSayaci:
    def __init__(self, butce: int = None):
        self.butce = DAKIKALIK_BUTCE if butce is None else butce
        self.r = _redis()
        self.yerel = 0
        if self.r is None:
            print("[finnhub_kota] UYARI: Redis'e ulasilamadi — dakikalik sayac "
                  "tutulamiyor, istekler sinirsiz gecer (fail-open).", flush=True)

    @property
    def _anahtar(self) -> str:
        return ONEK + _dakika()

    def kullanilan(self) -> int:
        if self.r is None:
            return self.yerel
        try:
            return int(self.r.get(self._anahtar) or 0)
        except Exception:
            return self.yerel

    def izin_var(self) -> bool:
        if self.r is None:
            return True  # fail-open
        return self.kullanilan() < self.butce

    def harca(self, adet: int = 1) -> None:
        self.yerel += adet
        if self.r is None:
            return
        try:
            p = self.r.pipeline()
            p.incrby(self._anahtar, adet)
            # 120 sn: dakika penceresi gecince anahtar kendiliginden dusar.
            p.expire(self._anahtar, 120)
            p.execute()
        except Exception:
            pass

    def durum(self) -> dict:
        k = self.kullanilan()
        return {
            "dakika_utc": _dakika(),
            "bu_servisin_butcesi": self.butce,
            "bu_dakika_kullanilan": k,
            "kalan": max(0, self.butce - k),
            "anahtar_basina_finnhub_limiti": ANAHTAR_BASINA_DAKIKA_LIMITI,
            "redis_bagli": self.r is not None,
            "not": ("Bu sayac YALNIZCA bu servisin tuketimini olcer. "
                    "Ayni anahtar havuzunu kullanan diger servislerin "
                    "(saa, news-monitor, oanda, godmode-execution) kendi "
                    "sayaci yoktur."),
        }


class KotaDoldu(RuntimeError):
    """Bu servisin dakikalik payi doldu; cagri YAPILMADI."""
