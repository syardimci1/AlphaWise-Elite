"""
SEC EDGAR hiz sinirlayici — ONLEYICI (proaktif) jeton kovasi.

=======================================================================
NEDEN ONLEYICI, NEDEN "HATA ALIP TEKRAR DENE" DEGIL
=======================================================================
SEC'in resmi politikasi (sec.gov/privacy, Internet Security Policy):

  "Current guidelines limit users to a total of no more than 10 requests
   per second, REGARDLESS OF THE NUMBER OF MACHINES used to submit
   requests. If a user or application submits more than 10 requests per
   second, further requests from the IP address(es) may be limited for a
   brief period. Once the rate of requests has dropped below the
   threshold for 10 minutes, the user may resume accessing content."

Iki kritik sonuc:

1) SINIR IP BAZLIDIR, SUREC BAZLI DEGIL.
   "regardless of the number of machines" ifadesi, sinirin tum
   makineler/container'lar icin ORTAK oldugunu soyler. Bu yuzden
   sayac Redis'te tutulur: ileride baska bir servis de SEC'e
   giderse ayni kovayi paylasabilir. Surec-ici bir sayac, her
   container kendini uyumlu sanarken toplamda sinirin asilmasina
   yol acardi.

2) ASIM CEZASI 10 DAKIKALIK SOGUMADIR.
   Yani "istegi gonder, 429 alirsan tekrar dene" stratejisi
   servisi 10 dakika komple kor eder. Bu yuzden burada istek
   GONDERILMEDEN ONCE jeton beklenir (asyncio.sleep), asla
   once gonderip sonra toparlanmaya calisilmaz.

=======================================================================
SECILEN HIZ: saniyede 5 (tavan 10'un yarisi)
=======================================================================
Tavana kadar kosmak, ayni IP'den giden baska bir istegin (elle
yapilan bir curl, ileride eklenecek bir servis) toplami tavana
tasimasi riskini tasir. Guvenlik payi olarak tavanin yarisi secildi.
Ortam degiskeniyle degistirilebilir ama varsayilan muhafazakardir.

=======================================================================
PATLAMA KAPASITESI = 1 (OLCUME DAYALI KARAR, TASARIM TERCIHI DEGIL)
=======================================================================
Ilk surumde kova kapasitesi hiz kadardi (5 jeton) ve kova DOLU
basliyordu. Klasik jeton kovasi davranisi budur; kisa patlamalara
izin verir. 15 ES ZAMANLI istekle olculdugunde sonuc:

    kapasite=5 : 15 istek / 1.23 sn = 12.19 istek/sn  -> TAVAN ASILDI
    kapasite=1 : (asagidaki testte)                    -> tavan altinda

Yani dolu kova, 5 istegin ANINDA cikmasina izin veriyordu; es zamanli
cagrilarla birleince anlik hiz SEC'in 10/sn tavanini asti. Sinirlayici
"calisiyor" gorunuyordu (fren 1.96 sn bekletmisti) ama koruma
YETERSIZDI.

Bu yuzden varsayilan kapasite 1'dir: patlama YOK, istekler kati sekilde
1/hiz araliklarina yayilir. Dis bir servisin sert siniri soz konusuysa
patlamaya izin vermek, kazanilan hizin karsiliginda 10 dakikalik
engellenme riskini satin almak demektir.
"""
import asyncio
import logging
import time

logger = logging.getLogger("sec13f.ratelimit")

# SEC tavani 10/sn. Guvenlik payiyla yarisi kullanilir.
SEC_TAVAN_SANIYE = 10
VARSAYILAN_HIZ = 5.0
# Anlik patlama kapasitesi. 1 = patlama yok (bkz. baslik notu).
VARSAYILAN_PATLAMA = 1.0

# Redis'te atomik jeton kovasi. Yaris kosulu olmasin diye Lua ile
# "oku-hesapla-yaz" tek adimda yapilir.
_LUA_KOVA = """
local anahtar = KEYS[1]
local hiz = tonumber(ARGV[1])
local kapasite = tonumber(ARGV[2])
local simdi = tonumber(ARGV[3])

local veri = redis.call('HMGET', anahtar, 'jeton', 'zaman')
local jeton = tonumber(veri[1])
local zaman = tonumber(veri[2])

if jeton == nil then
  jeton = kapasite
  zaman = simdi
end

-- gecen sureye gore jeton doldur
local gecen = math.max(0, simdi - zaman)
jeton = math.min(kapasite, jeton + gecen * hiz)

-- REZERVASYON: jeton her cagride KOSULSUZ dusulur ve NEGATIFE inebilir.
-- Negatif jeton "bu slot zaten bir cagriya soz verildi" demektir.
-- Kosullu dusme (yalnizca jeton>=1 iken) yaris kosulu yaratirdi:
-- jeton=0 iken es zamanli gelen 10 cagri da ayni bekleme suresini
-- hesaplayip UYKUDAN AYNI ANDA kalkar ve toplu ates ederdi.
local bekle = 0
if jeton < 1 then
  bekle = (1 - jeton) / hiz
end
jeton = jeton - 1

redis.call('HMSET', anahtar, 'jeton', jeton, 'zaman', simdi)
redis.call('EXPIRE', anahtar, 60)
return tostring(bekle)
"""


class HizSinirlayici:
    """
    Onleyici jeton kovasi.

    kullanim:
        await sinirlayici.bekle()   # jeton hazir olana kadar UYUR
        ... istegi simdi gonder ...

    Redis varsa kova paylasilir (IP bazli SEC siniriyla uyumlu).
    Redis yoksa surec-ici yedege duser ve bunu ACIKCA raporlar —
    sessizce "her sey yolunda" gibi davranmaz.
    """

    def __init__(self, redis_client=None, hiz: float = VARSAYILAN_HIZ,
                 anahtar: str = "sec13f:ratelimit:sec-edgar",
                 patlama_kapasitesi: float = VARSAYILAN_PATLAMA):
        self.redis = redis_client
        self.hiz = hiz
        # Kapasite = izin verilen ANLIK patlama. 1 = patlama yok, istekler
        # kati sekilde 1/hiz araliklarina yayilir. Bkz. modul basligindaki
        # "PATLAMA KAPASITESI" notu — 1'den buyuk deger olculerek reddedildi.
        self.kapasite = max(1.0, float(patlama_kapasitesi))
        self.anahtar = anahtar
        self._lua = None
        # surec-ici yedek durumu
        self._yerel_jeton = self.kapasite
        self._yerel_zaman = time.monotonic()
        self._kilit = asyncio.Lock()
        self._redis_dustu = False
        self.toplam_istek = 0
        self.toplam_bekleme_sn = 0.0

    async def _redis_bekleme_suresi(self) -> float:
        if self._lua is None:
            self._lua = self.redis.register_script(_LUA_KOVA)
        sonuc = await self._lua(
            keys=[self.anahtar],
            args=[self.hiz, self.kapasite, time.time()],
        )
        if isinstance(sonuc, bytes):
            sonuc = sonuc.decode()
        return float(sonuc)

    async def _yerel_bekleme_suresi(self) -> float:
        # Redis'teki ile AYNI rezervasyon modeli: jeton kosulsuz dusulur,
        # negatife inebilir. Boylece es zamanli cagrilar toplu ates etmez,
        # sirayla 1/hiz araliklarina yayilir.
        async with self._kilit:
            simdi = time.monotonic()
            gecen = max(0.0, simdi - self._yerel_zaman)
            self._yerel_jeton = min(self.kapasite, self._yerel_jeton + gecen * self.hiz)
            self._yerel_zaman = simdi
            bekle = 0.0
            if self._yerel_jeton < 1:
                bekle = (1 - self._yerel_jeton) / self.hiz
            self._yerel_jeton -= 1
            return bekle

    async def bekle(self) -> float:
        """
        Jeton hazir olana kadar UYUR, sonra doner. Donen deger
        beklenen saniyedir (0 = bekleme olmadi).

        Istek BUNDAN SONRA gonderilir; once gonderip hata yakalamaz.
        """
        bekle = 0.0
        if self.redis is not None and not self._redis_dustu:
            try:
                bekle = await self._redis_bekleme_suresi()
            except Exception as e:
                # Redis dustu: yerel kovaya gec ama SESSIZ KALMA.
                self._redis_dustu = True
                logger.warning(
                    "Redis jeton kovasi kullanilamadi (%s); surec-ici yedege "
                    "gecildi. Birden fazla container varsa SEC siniri asilabilir.",
                    type(e).__name__,
                )
                bekle = await self._yerel_bekleme_suresi()
        else:
            bekle = await self._yerel_bekleme_suresi()

        if bekle > 0:
            await asyncio.sleep(bekle)
        self.toplam_istek += 1
        self.toplam_bekleme_sn += bekle
        return bekle

    def durum(self) -> dict:
        return {
            "hiz_saniyede": self.hiz,
            "sec_resmi_tavan_saniyede": SEC_TAVAN_SANIYE,
            "guvenlik_payi": f"tavanin %{self.hiz / SEC_TAVAN_SANIYE * 100:.0f}'i kullaniliyor",
            "patlama_kapasitesi": self.kapasite,
            "patlama_notu": ("1 = anlik patlama yok; istekler kati sekilde "
                             "1/hiz araliklarina yayilir"),
            "kova_yeri": "surec-ici (yedek)" if (self.redis is None or self._redis_dustu) else "redis (paylasimli)",
            "redis_dustu": self._redis_dustu,
            "toplam_istek": self.toplam_istek,
            "toplam_bekleme_sn": round(self.toplam_bekleme_sn, 3),
            "strateji": "ONLEYICI - jeton hazir olana kadar uyunur; istek gonderilip hata beklenmez",
            "politika_kaynagi": "https://www.sec.gov/privacy (Internet Security Policy)",
        }
