"""
Tarihsel kriz stres testi (Madde 26).

NE YAPAR
========
Bir hissenin, gecmiste GERCEKTEN yasanmis kriz pencerelerinde nasil
davrandigini olcer: donem getirisi ve donem ICI en buyuk deger dususu
(maximum drawdown).

PENCERELER NEDEN BOYLE SECILDI
==============================
Pencereler "kriz yili" gibi kaba araliklar degil, genis kabul goren zirve
-> dip tarihleridir. Takvim yili kullanmak olcumu sulandirirdi: 2020'nin
tamami alindiginda COVID cokusu ve onu izleyen toparlanma birbirini goturur
ve "kriz" neredeyse gorunmez olur.

OLCULEMEDI != SIFIR
===================
Hisse o tarihte islem gormuyorsa (halka arz sonrasi) sonuc SIFIR degil
OLCULEMEDI'dir. Sifir yazmak, krizden hic etkilenmemis gibi gostererek
genc sirketleri yapay olarak dayanikli gosterirdi.
"""
from __future__ import annotations
from typing import Optional

# Zirve -> dip tarihleri (S&P 500 kapanis bazli, genis kabul goren tarihler).
# Tarihler koda GOMULU ve gerekceli: her biri ciktida da bildirilir.
KRIZLER = [
    {"anahtar": "kuresel_finans_2008", "ad": "Küresel Finans Krizi",
     "baslangic": "2007-10-09", "bitis": "2009-03-09",
     "aciklama": "S&P 500'ün 2007 zirvesinden 2009 dibine kadar geçen dönem."},
    {"anahtar": "covid_2020", "ad": "COVID-19 Çöküşü",
     "baslangic": "2020-02-19", "bitis": "2020-03-23",
     "aciklama": "Beş haftada gerçekleşen, modern dönemin en hızlı düşüşü."},
    {"anahtar": "ayi_piyasasi_2022", "ad": "2022 Ayı Piyasası",
     "baslangic": "2022-01-03", "bitis": "2022-10-12",
     "aciklama": "Faiz artışlarıyla gelen, yaklaşık on aya yayılan düşüş."},
]

# Bir pencerenin olculmus sayilmasi icin gereken en az islem gunu. Bes
# gunluk bir kesit "krizde nasil davrandi" sorusunu yanitlamaz.
ASGARI_GUN = 20


def maksimum_dusus(fiyatlar: list) -> Optional[float]:
    """En yuksek zirveden sonraki en derin dusus orani (0-1 arasi, pozitif).

    Tanim: max_t [(o ana kadarki zirve - fiyat_t) / o ana kadarki zirve]
    Yalnizca YUKSELEN bir seride 0.0 doner; bu GECERLI bir olcumdur.
    """
    temiz = [float(f) for f in fiyatlar
             if f is not None and float(f) == float(f) and float(f) > 0]
    if len(temiz) < 2:
        return None
    zirve = temiz[0]
    en_derin = 0.0
    for f in temiz[1:]:
        if f > zirve:
            zirve = f
        dusus = (zirve - f) / zirve
        if dusus > en_derin:
            en_derin = dusus
    return en_derin


def donem_getirisi(fiyatlar: list) -> Optional[float]:
    temiz = [float(f) for f in fiyatlar
             if f is not None and float(f) == float(f) and float(f) > 0]
    if len(temiz) < 2:
        return None
    return temiz[-1] / temiz[0] - 1.0


def pencere_olc(seri: dict, baslangic: str, bitis: str,
                asgari_gun: int = ASGARI_GUN) -> dict:
    """seri: {tarih(YYYY-MM-DD): kapanis}. Pencere ICINDEKI gunler olculur."""
    gunler = sorted(t for t in seri if baslangic <= t <= bitis)
    if len(gunler) < asgari_gun:
        return {"durum": "olculemedi", "getiri": None, "maksimum_dusus": None,
                "islem_gunu": len(gunler),
                "gerekce": (f"Bu pencerede yalnızca {len(gunler)} işlem günü "
                            f"verisi var (en az {asgari_gun} gerekiyor); hisse "
                            f"o dönemde işlem görmüyor olabilir. Bu bir ölçüm "
                            f"eksikliğidir, sıfır etki değildir.")}
    fiyatlar = [seri[g] for g in gunler]
    return {"durum": "olculdu",
            "getiri": donem_getirisi(fiyatlar),
            "maksimum_dusus": maksimum_dusus(fiyatlar),
            "islem_gunu": len(gunler),
            "ilk_gun": gunler[0], "son_gun": gunler[-1],
            "gerekce": ""}


def tarihsel_stres(seri: dict, krizler: list = None,
                   asgari_gun: int = ASGARI_GUN) -> list:
    cikti = []
    for k in (krizler or KRIZLER):
        olcum = pencere_olc(seri, k["baslangic"], k["bitis"], asgari_gun)
        cikti.append({**k, **olcum})
    return cikti
