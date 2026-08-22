"""
FMP gunluk kota sayaci — kullanici-yuzu servisleri arka plan islerinden korur.

=======================================================================
NEDEN VAR (olculen sorun, 22.08.2026)
=======================================================================
AYNI FMP_API_KEY iki yerde kullaniliyor (deger karsilastirmasiyla
dogrulandi, sha256 esit):
  - congress-trading-service : KULLANICI ISTEGIYLE tetiklenir, dashboard
    kartini besler. Redis onbellegi 1 saat oldugundan gunluk AZAMI
    2 istek x 24 = 48 cagri yapar.
  - qlib-service/data_prep/bulk_fetch_fmp_us.py : ARKA PLAN toplu cekme.
    progress.json'daki basarisiz hisseleri dener; su an 160 hisse =
    tek calistirmada 160 cagri. Zamanlanmis DEGIL (crontab'da ve
    weekly_retrain.sh'de yok), elle calistiriliyor; son calistirma
    16 Agustos.

(Ucuncu bir tuketici gibi gorunen faa/src/main.py'nin FMP yedegi ise
FIILEN OLU: container'da FMP_API_KEY tanimli degil, fonksiyon anahtar
bulamayip hemen None donuyor. Dogrulandi.)

Yani risk GUNLUK degil, KOSULLU: yalnizca toplu cekme elle calistirilan
gunlerde iki tuketici ayni kotayi paylasiyor. O gun toplam ~208 cagri
oluyor ve toplu is, kullanici-yuzu servisin payini yiyebilir.

FMP bu planda kalan kotayi ne yanit basliginda ne de bir hesap
endpoint'inde bildiriyor (ikisi de denendi); bu yuzden tavan
OLCULEMEZ, disaridan verilmesi gerekir. Varsayilan 250, FMP'nin
yaygin ucretsiz katman degeridir — dogru deger biliniyorsa
FMP_GUNLUK_TAVAN ile gecilmelidir.

=======================================================================
NASIL CALISIR
=======================================================================
Gun bazli bir Redis sayaci (UTC) tutulur. Arka plan isi, sayaci
artirmadan once "bu istegi yaparsam kullanici-yuzu servise ayrilan
rezervin altina duser miyim" diye bakar; duserse DURUR. Boylece
congress-trading'in gunluk payi arka plan isi tarafindan tuketilemez.

Redis yoksa FAIL-OPEN calisir: sayac tutulamaz ama is durmaz, yalnizca
uyari yazilir — mevcut davranis bozulmaz.
"""
import datetime
import os

VARSAYILAN_TAVAN = int(os.getenv("FMP_GUNLUK_TAVAN", "250"))
# congress-trading'in gunluk azami tuketimi 48; yuvarlanip pay birakildi.
VARSAYILAN_REZERV = int(os.getenv("FMP_KULLANICI_REZERVI", "60"))
ONEK = "fmp:gunluk:"


def _bugun() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


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


class KotaSayaci:
    """
    Arka plan isleri icin kota bekcisi.

    kullanim:
        k = KotaSayaci("bulk_fetch_fmp_us")
        for ticker in liste:
            if not k.izin_var():
                break          # rezervi koru, kullanici-yuzu servisi ac birakma
            ... istegi yap ...
            k.harca()
    """

    def __init__(self, is_adi: str, tavan: int = None, rezerv: int = None):
        self.is_adi = is_adi
        self.tavan = VARSAYILAN_TAVAN if tavan is None else tavan
        self.rezerv = VARSAYILAN_REZERV if rezerv is None else rezerv
        self.r = _redis()
        self.yerel_harcama = 0
        self.durdu = False
        if self.r is None:
            print(
                "[fmp_kota] UYARI: Redis'e ulasilamadi — gunluk kota sayaci "
                "tutulamiyor, is sinirsiz devam edecek (fail-open).",
                flush=True,
            )

    @property
    def _anahtar(self) -> str:
        return ONEK + _bugun()

    def kullanilan(self) -> int:
        if self.r is None:
            return self.yerel_harcama
        try:
            return int(self.r.get(self._anahtar) or 0)
        except Exception:
            return self.yerel_harcama

    def arka_plan_butcesi(self) -> int:
        """Arka plan isinin kullanabilecegi azami cagri (rezerv dusulmus)."""
        return max(0, self.tavan - self.rezerv)

    def izin_var(self) -> bool:
        if self.r is None:
            return True  # fail-open
        kalan = self.arka_plan_butcesi() - self.kullanilan()
        if kalan <= 0 and not self.durdu:
            self.durdu = True
            print(
                f"[fmp_kota] DURDURULDU: gunluk arka plan butcesi doldu "
                f"({self.kullanilan()}/{self.arka_plan_butcesi()}). "
                f"Kalan {self.rezerv} cagri kullanici-yuzu servis "
                f"(congress-trading) icin REZERVE edildi.",
                flush=True,
            )
        return kalan > 0

    def harca(self, adet: int = 1) -> None:
        self.yerel_harcama += adet
        if self.r is None:
            return
        try:
            p = self.r.pipeline()
            p.incrby(self._anahtar, adet)
            p.expire(self._anahtar, 48 * 3600)
            p.execute()
        except Exception:
            pass

    def ozet(self) -> str:
        return (
            f"[fmp_kota] {self.is_adi}: bu calistirmada {self.yerel_harcama} cagri | "
            f"bugun toplam {self.kullanilan()}/{self.tavan} "
            f"(arka plan butcesi {self.arka_plan_butcesi()}, "
            f"kullanici rezervi {self.rezerv})"
        )
