"""Patent kaynagi — Google Patents dahili XHR uc noktasi.

BU KAYNAK NEDEN SECILDI (olculerek)
===================================
09-10.09.2026'da resmi patent API'lerinin tamami olculdu:

  https://api.uspto.gov/api/v1/...        -> HTTP 401 Unauthorized (anahtar sart)
  https://api.patentsview.org/...         -> emekli; data.uspto.gov'a yonlendiriyor
  https://search.patentsview.org/...      -> baglanti kurulamadi
  https://bulkdata.uspto.gov/             -> baglanti kurulamadi (emekli)
  https://ops.epo.org/3.2/...             -> HTTP 403 (anahtar sart)
  https://worldwide.espacenet.com/...     -> HTTP 403
  https://patents.google.com/xhr/query    -> HTTP 200, anahtarsiz  <-- tek acik yol

Yani "ucretsiz ama kayit gerektiren" anahtar alinmadan calisan TEK kaynak bu.

KAYNAK KIRILGANDIR — VE BU GIZLENMEZ
====================================
Bu uc nokta Google tarafindan BELGELENMEMISTIR. Sema degisebilir, hiz siniri
gelebilir, tamamen kapanabilir. Bu yuzden burada tek bir kural gecerlidir:

    Kaynak cevap veremediginde SIFIR DONULMEZ, "OLCULEMEDI" donulur.

"Bu sirketin patenti yok" ile "patent sayisini ogrenemedik" ayni sey degildir.
Ilkini ikincisinin yerine yazmak, bu depoda 232d1a0 ile kapatilan hatanin
aynisidir. Bu yuzden modul Olcum sozlesmesini kullanir ve OLCULDU durumunda
bile kaynagin kirilganligini `ayrinti["kaynak_kirilgan"]` ile isaretler.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from olcum import OLCULDU, OLCULEMEDI, Olcum

UC_NOKTA = "https://patents.google.com/xhr/query"
KULLANICI_AJANI = "Mozilla/5.0 (X11; Linux x86_64)"
ZAMAN_ASIMI = 30


class KaynakHatasi(Exception):
    """Kaynaga ulasilamadi ya da beklenen sema gelmedi."""


def _istek(sorgu: str, acan=None) -> dict:
    url = UC_NOKTA + "?url=" + urllib.parse.quote(sorgu, safe="")
    istek = urllib.request.Request(url, headers={"User-Agent": KULLANICI_AJANI})
    ac = acan or urllib.request.urlopen
    try:
        with ac(istek, timeout=ZAMAN_ASIMI) as yanit:
            ham = yanit.read()
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise KaynakHatasi(f"kaynaga ulasilamadi: {e}") from e
    try:
        return json.loads(ham)
    except (ValueError, TypeError) as e:
        # Google hata sayfasi dondurdugunde HTML gelir — sessizce 0 sayilmamali.
        raise KaynakHatasi("kaynak JSON yerine baska bir sey dondu "
                           "(muhtemelen hata sayfasi veya hiz siniri)") from e


def _sonuc_govdesi(d: dict) -> dict:
    if not isinstance(d, dict) or "results" not in d:
        raise KaynakHatasi("beklenen 'results' alani yok — sema degismis olabilir")
    r = d["results"]
    if not isinstance(r, dict):
        raise KaynakHatasi("'results' beklenen sozluk turunde degil")
    return r


def sorgu_sayisi(sorgu: str, acan=None) -> Olcum:
    """Bir sorgunun toplam patent sayisini olcer.

    Sayi 0 olabilir ve bu GERCEK bir olcumdur (OLCULDU). Kaynak cevap
    veremezse OLCULEMEDI doner — ikisi karistirilmaz.
    """
    try:
        r = _sonuc_govdesi(_istek(sorgu, acan))
    except KaynakHatasi as e:
        return Olcum(None, OLCULEMEDI, gerekce=str(e),
                     ayrinti={"sorgu": sorgu, "kaynak_kirilgan": True})
    n = r.get("total_num_results")
    if n is None:
        return Olcum(None, OLCULEMEDI,
                     gerekce="kaynak 'total_num_results' alanini dondurmedi",
                     eksik=("total_num_results",),
                     ayrinti={"sorgu": sorgu, "kaynak_kirilgan": True})
    if not isinstance(n, (int, float)) or isinstance(n, bool) or n < 0:
        return Olcum(None, OLCULEMEDI,
                     gerekce=f"'total_num_results' sayi degil ya da negatif: {n!r}",
                     ayrinti={"sorgu": sorgu, "kaynak_kirilgan": True})
    return Olcum(float(n), OLCULDU,
                 ayrinti={"sorgu": sorgu, "kaynak_kirilgan": True})


def ornek_kayitlar(sorgu: str, adet: int = 10, acan=None) -> list:
    """Sorgunun ilk sonuclarini dondurur (eslesme dogrulamasi icin).

    Hata durumunda BOS LISTE DEGIL, KaynakHatasi firlatir — bos liste
    "sonuc yok" ile karisirdi.
    """
    r = _sonuc_govdesi(_istek(sorgu, acan))
    kayitlar = []
    for kume in r.get("cluster") or []:
        for satir in kume.get("result") or []:
            p = satir.get("patent") or {}
            kayitlar.append({
                "numara": p.get("publication_number"),
                "baslik": p.get("title"),
                "sahip": p.get("assignee"),
                "basvuru_tarihi": p.get("filing_date"),
                "oncelik_tarihi": p.get("priority_date"),
                "yayin_tarihi": p.get("publication_date"),
            })
            if len(kayitlar) >= adet:
                return kayitlar
    return kayitlar
