"""GEX sonuc onbellegi testleri — Madde 36.

En onemli test test_onbellek_isabetinde_kota_HIC_tuketilmez: onbellek
kota AYRILDIKTAN sonra okunsaydi hicbir tasarruf saglamazdi. Bu testler
o sirayi davranissal olarak kilitler, kod okuyarak degil.
"""
import asyncio
import json
import sys

import pytest

sys.path.insert(0, "/app")

import gex_onbellek as go  # noqa: E402


# ------------------------------------------------------- saf fonksiyonlar
def test_anahtar_vadeyi_icerir():
    """Farkli vade = farkli veri; tek anahtarda toplamak yanlis GEX dondururdu."""
    a = go.onbellek_anahtari("MSFT", "2026-10-16")
    b = go.onbellek_anahtari("MSFT", "2026-11-20")
    c = go.onbellek_anahtari("MSFT", None)
    assert a != b and a != c and b != c
    assert a.startswith("gex:sonuc:MSFT:")


def test_anahtar_normalize_eder():
    assert go.onbellek_anahtari(" msft ", None) == go.onbellek_anahtari("MSFT", "")
    assert go.onbellek_anahtari("MSFT", None).endswith(":tum")


def test_anahtar_kota_alan_adiyla_carpismaz():
    """Kota sayaclari 'gex:quota:' onekini kullaniyor — carpisma olmamali."""
    assert not go.onbellek_anahtari("MSFT", None).startswith("gex:quota:")


def test_tazelik_metni_taze():
    m = go.tazelik_metni(0, 900)
    assert "az once alindi" in m and "15 dakika" in m


def test_tazelik_metni_toplam_gecikmeyi_gizlemez():
    """Onbellek, veriyi oldugundan taze gostermenin araci DEGILDIR."""
    m = go.tazelik_metni(300, 900)
    assert "300 sn once" in m
    assert "en fazla ~30 dakika" in m, (
        "kaynak gecikmesi + onbellek TTL toplami bildirilmeli")


@pytest.mark.parametrize("ttl,beklenen_dk", [(900, 30), (60, 16), (0, 15), (61, 17)])
def test_azami_gecikme_yukari_yuvarlanir(ttl, beklenen_dk):
    """Kismi dakika asagi yuvarlanirsa gecikme oldugundan az bildirilir."""
    assert f"~{beklenen_dk} dakika" in go.tazelik_metni(1, ttl)


def test_saklanacak_govde_kotayi_saklamaz():
    """Saklanan kota bilgisi dakikalar icinde yanlislasir."""
    y = {"ticker": "MSFT", "gex": {"net": 5}, "kota_durumu": {"toplam_kalan": 24},
         "onbellekten": False, "onbellek_yasi_saniye": 0,
         "veri_tazeligi": "x", "flashalpha_kotasi_tuketildi": False}
    g = go.saklanacak_govde(y, 1000.0)
    assert "kota_durumu" not in g and "onbellekten" not in g
    assert "veri_tazeligi" not in g and "onbellek_yasi_saniye" not in g
    assert g["gex"] == {"net": 5} and g["_alindi_ts"] == 1000.0


def test_isabet_yaniti_canli_kota_kullanir():
    g = go.saklanacak_govde({"ticker": "MSFT", "gex": {"net": 5},
                             "kota_durumu": {"toplam_kalan": 24}}, 1000.0)
    y = go.isabet_yaniti(g, 1300.0, 900, {"toplam_kalan": 7})
    assert y["kota_durumu"] == {"toplam_kalan": 7}, "saklanan kota kullanilmis"
    assert y["onbellekten"] is True
    assert y["onbellek_yasi_saniye"] == 300
    assert y["flashalpha_kotasi_tuketildi"] is False
    assert y["gex"] == {"net": 5}


def test_isabet_yaniti_govdedeki_kotayi_ASLA_kullanmaz():
    """Iki katmanli savunma.

    saklanacak_govde zaten kota_durumu'nu ayikliyor, ama isabet_yaniti
    TEK BASINA da guvenli olmali: eski bicimde yazilmis ya da baska bir
    yoldan gelmis bir govde kota tasiyorsa, kullaniciya BAYAT bir hak
    gosterilirdi ("24 hakkin var" derken hak bitmis olabilir).
    """
    saklanan = {"ticker": "MSFT", "_alindi_ts": 1000.0,
                "kota_durumu": {"toplam_kalan": 24}}
    y = go.isabet_yaniti(saklanan, 1100.0, 900, {"toplam_kalan": 0})
    assert y["kota_durumu"] == {"toplam_kalan": 0}, (
        "govdedeki bayat kota sunuldu")


def test_isabet_yaniti_ic_alanlari_sizdirmaz():
    g = go.saklanacak_govde({"ticker": "MSFT"}, 1000.0)
    y = go.isabet_yaniti(g, 1000.0, 900, {})
    assert not [k for k in y if k.startswith("_")], f"ic alan sizdi: {y}"


def test_isabet_yaniti_negatif_yas_uretmez():
    """Saat geri alinirsa yas negatif gorunmemeli."""
    g = go.saklanacak_govde({"ticker": "MSFT"}, 2000.0)
    assert go.isabet_yaniti(g, 1000.0, 900, {})["onbellek_yasi_saniye"] == 0


def test_zaman_damgasi_yoksa_yas_sifir():
    y = go.isabet_yaniti({"ticker": "MSFT"}, 1500.0, 900, {})
    assert y["onbellek_yasi_saniye"] == 0


def test_gidis_donus_veriyi_bozmaz():
    ozgun = {"ticker": "MSFT", "expiration": "2026-10-16",
             "gex": {"net_gex": -1.23e9, "seviyeler": [1, 2, 3]},
             "kullanilan_anahtar": "FLASHALPHA_API_KEY_2"}
    g = json.loads(json.dumps(go.saklanacak_govde(dict(ozgun), 1000.0)))
    y = go.isabet_yaniti(g, 1000.0, 900, {})
    for k, v in ozgun.items():
        assert y[k] == v, f"{k} bozuldu: {y[k]!r} != {v!r}"


# --------------------------------------------- davranissal: kota tasarrufu
class _SahteRedis:
    """TEK ad alani — gercek Redis gibi.

    Kota sayaclarini ve onbellek govdelerini ayri sozluklerde tutmak,
    "gex:sonuc:" ile "gex:quota:" anahtarlarinin carpisip carpismadigini
    test EDILEMEZ hale getirirdi.
    """

    def __init__(self):
        self.depo = {}

    def get(self, k):
        v = self.depo.get(k)
        return str(v) if isinstance(v, int) else v

    def setex(self, k, ttl, v):
        self.depo[k] = v

    def incr(self, k):
        self.depo[k] = int(self.depo.get(k, 0)) + 1
        return self.depo[k]

    def decr(self, k):
        self.depo[k] = int(self.depo.get(k, 0)) - 1
        return self.depo[k]

    def expire(self, k, ttl):
        return True

    def ping(self):
        return True


class _SahteYanit:
    status_code = 200
    text = "{}"

    def json(self):
        return {"net_gex": 123.0}


class _SahteIstemci:
    cagri_sayisi = 0

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        _SahteIstemci.cagri_sayisi += 1
        return _SahteYanit()


@pytest.fixture
def kurulu_main(monkeypatch):
    monkeypatch.setenv("FLASHALPHA_API_KEY_1", "sahte-anahtar-1")
    monkeypatch.setenv("FLASHALPHA_API_KEY_2", "sahte-anahtar-2")
    import importlib
    import main as m
    importlib.reload(m)
    sahte = _SahteRedis()
    monkeypatch.setattr(m, "_get_redis", lambda: sahte)
    monkeypatch.setattr(m.httpx, "AsyncClient", _SahteIstemci)
    _SahteIstemci.cagri_sayisi = 0
    return m, sahte


def test_ilk_istek_kota_tuketir_ikincisi_TUKETMEZ(kurulu_main):
    """Maddenin somut ciktisi: ayni sembol ikinci kez sorulunca hak yanmaz."""
    m, sahte = kurulu_main
    ilk = asyncio.run(m.gamma_exposure("MSFT", expiration=None))
    assert ilk["onbellekten"] is False
    assert _SahteIstemci.cagri_sayisi == 1
    kullanilan_sonra = m.kota_durumu()["toplam_kullanilan"]

    ikinci = asyncio.run(m.gamma_exposure("MSFT", expiration=None))
    assert ikinci["onbellekten"] is True
    assert _SahteIstemci.cagri_sayisi == 1, "ikinci istek FlashAlpha'ya gitti"
    assert m.kota_durumu()["toplam_kullanilan"] == kullanilan_sonra, (
        "onbellek isabetinde kota sayaci artti")
    assert ikinci["gex"] == ilk["gex"]


def test_farkli_vade_onbellegi_paylasmaz(kurulu_main):
    m, _ = kurulu_main
    asyncio.run(m.gamma_exposure("MSFT", expiration="2026-10-16"))
    asyncio.run(m.gamma_exposure("MSFT", expiration="2026-11-20"))
    assert _SahteIstemci.cagri_sayisi == 2, "farkli vade onbellekten donduruldu"


def test_farkli_sembol_onbellegi_paylasmaz(kurulu_main):
    m, _ = kurulu_main
    asyncio.run(m.gamma_exposure("MSFT", expiration=None))
    asyncio.run(m.gamma_exposure("NVDA", expiration=None))
    assert _SahteIstemci.cagri_sayisi == 2


def test_kota_dolu_olsa_bile_onbellek_sunulur(kurulu_main):
    """Onbellekteki yanit istek gerektirmez; kota doldu diye reddedilmemeli."""
    m, sahte = kurulu_main
    asyncio.run(m.gamma_exposure("MSFT", expiration=None))
    for ad, _ in m._flashalpha_anahtarlari():          # tum kotalari doldur
        sahte.depo[m._kota_redis_anahtari(ad)] = m.ANAHTAR_BASINA_GUNLUK_KOTA
    assert m.kota_durumu()["kota_doldu"] is True
    y = asyncio.run(m.gamma_exposure("MSFT", expiration=None))
    assert y["onbellekten"] is True and _SahteIstemci.cagri_sayisi == 1


def test_kota_dolu_ve_onbellek_yoksa_429(kurulu_main):
    """Onbellek kota kontrolunu ATLATMAMALI — bos onbellekte yine 429."""
    from fastapi import HTTPException
    m, sahte = kurulu_main
    for ad, _ in m._flashalpha_anahtarlari():
        sahte.depo[m._kota_redis_anahtari(ad)] = m.ANAHTAR_BASINA_GUNLUK_KOTA
    with pytest.raises(HTTPException) as e:
        asyncio.run(m.gamma_exposure("NVDA", expiration=None))
    assert e.value.status_code == 429
    assert e.value.detail["istek_yapilmadi"] is True
    assert _SahteIstemci.cagri_sayisi == 0


def test_kota_sayilamiyorsa_istek_YAPILMAZ(kurulu_main):
    """Redis dusukse sinirli kaynak harcanmamali.

    "Sayamadik" ile "hakkin var" ayni sey degildir: sayilamayan bir kotayi
    harcamak, gunluk butcenin muhasebesiz tukenmesi demektir. Onceki
    davranis burada ciplak bir RuntimeError ile 500 uretiyordu.
    """
    from fastapi import HTTPException
    m, _ = kurulu_main

    class _Bozuk:
        def __getattr__(self, ad):
            def _patla(*a, **k):
                raise RuntimeError("redis yok")
            return _patla

    m._get_redis = lambda: _Bozuk()
    with pytest.raises(HTTPException) as e:
        asyncio.run(m.gamma_exposure("MSFT", expiration=None))
    assert e.value.status_code == 503
    assert e.value.detail["istek_yapilmadi"] is True
    assert "Kota sayaci okunamadi" in e.value.detail["hata"]
    assert _SahteIstemci.cagri_sayisi == 0, "kota sayilamazken istek gitti"


def test_hatali_yanit_onbelleklenmez(kurulu_main):
    """Gecici bir 502'yi 15 dk sunmak arizayi kalici hale getirirdi."""
    from fastapi import HTTPException
    m, sahte = kurulu_main

    class _Hata502(_SahteIstemci):
        async def get(self, *a, **k):
            _SahteIstemci.cagri_sayisi += 1
            y = _SahteYanit()
            y.status_code = 500
            y.text = "sunucu hatasi"
            return y

    m.httpx.AsyncClient = _Hata502
    with pytest.raises(HTTPException):
        asyncio.run(m.gamma_exposure("TSLA", expiration=None))
    assert not [k for k in sahte.depo if "TSLA" in k], "hata onbelleklendi"


def test_gecersiz_vade_turu_sessizce_gecistirilmez():
    """Query nesnesi gibi bir tur gelirse 'tum vadeler' diye anahtarlamak
    YANLIS vadenin GEX'ini onbellekten sunmak olurdu."""
    class _Sahte:
        pass
    with pytest.raises(TypeError):
        go.onbellek_anahtari("MSFT", _Sahte())
    with pytest.raises(TypeError):
        go.onbellek_anahtari(_Sahte(), None)


def test_onbellek_anahtari_kota_sayacini_EZMEZ(kurulu_main):
    """Ayni Redis ad alaninda kota sayaclariyla carpisma olmamali."""
    m, sahte = kurulu_main
    asyncio.run(m.gamma_exposure("MSFT", expiration=None))
    onceki = m.kota_durumu()["toplam_kullanilan"]
    assert onceki == 1
    kota_anahtarlari = {m._kota_redis_anahtari(ad)
                        for ad, _ in m._flashalpha_anahtarlari()}
    onbellek_anahtarlari = {k for k in sahte.depo if k.startswith("gex:sonuc:")}
    assert onbellek_anahtarlari and not (kota_anahtarlari & onbellek_anahtarlari)
