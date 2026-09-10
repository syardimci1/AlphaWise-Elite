"""Patent basvuru momentumu — yenilik yogunlugunun degisimi.

OLCULEN SEY
===========
Bir sirketin patent basvuru hizi hizlaniyor mu, yavasliyor mu. Iki ES UZUNLUKTA
pencerenin oncelik tarihli patent sayilari oranlanir.

EN BUYUK TUZAK: YAYIN GECIKMESI
===============================
Patent basvurusu, basvuru tarihinden yaklasik 18 ay SONRA yayimlanir; yayimlanana
kadar hicbir acik veri kaynaginda gorunmez. Dolayisiyla "son 12 ay" penceresi
HER sirkette eksik doludur.

Bunun sonucu ciddidir: son 12 ayi onceki 12 ayla karsilastiran bir olcum,
sirket ne yaparsa yapsin HER ZAMAN dususe isaret eder. Bu, veriden gelen
gercek bir sinyal degil, olcum yonteminin urettigi sahte bir sinyaldir — ve
onu "yenilik yavasliyor" diye raporlamak, olculmemis bir seyi olculmus gibi
gostermektir.

COZUM: OLGUNLASMAMIS PENCEREYE HIC BAKILMAZ
===========================================
Su andan geriye dogru `olgunluk_ay` kadarlik dilim ATILIR. Karsilastirilan iki
pencere de bu dilimin GERISINDEDIR, yani ikisi de tam dolmustur. Bunun bedeli,
sinyalin dogasi geregi gecikmeli olmasidir; bu bedel gizlenmez, `ayrinti`
icinde `veri_bitis_tarihi` olarak bildirilir.

Modul, olgunlasmamis dilime tasan bir pencere istendiginde SESSIZCE
duzeltmez — OLCULEMEDI dondurur. Otomatik duzeltme, kullanicinin istedigi
donemle raporlanan donemin sessizce farklilasmasi demektir.
"""
from __future__ import annotations

from datetime import date

from kaynak import sorgu_sayisi
from olcum import OLCULDU, OLCULEMEDI, Olcum

# Yayin gecikmesi 18 ay; guvenlik payiyla 24 ay atilir.
VARSAYILAN_OLGUNLUK_AY = 24


def _ay_ekle(t: date, ay: int) -> date:
    toplam = (t.year * 12 + (t.month - 1)) + ay
    yil, ay_no = divmod(toplam, 12)
    gun = min(t.day, [31, 29 if yil % 4 == 0 and (yil % 100 != 0 or yil % 400 == 0)
                      else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][ay_no])
    return date(yil, ay_no + 1, gun)


def veri_bitis_tarihi(bugun: date, olgunluk_ay: int = VARSAYILAN_OLGUNLUK_AY) -> date:
    """Verinin guvenilir sayilabildigi son tarih."""
    return _ay_ekle(bugun, -olgunluk_ay)


def pencere_sayisi(sahip: str, baslangic: date, bitis: date, acan=None) -> Olcum:
    """Bir sahibin verilen oncelik tarihi araligindaki patent sayisi."""
    if baslangic >= bitis:
        return Olcum(None, OLCULEMEDI,
                     gerekce=f"gecersiz aralik: {baslangic} >= {bitis}")
    sorgu = (f'q=assignee:"{sahip}"'
             f'&after=priority:{baslangic:%Y%m%d}'
             f'&before=priority:{bitis:%Y%m%d}')
    o = sorgu_sayisi(sorgu, acan=acan)
    if o.var_mi:
        return Olcum(o.deger, OLCULDU,
                     ayrinti={**o.ayrinti, "baslangic": baslangic.isoformat(),
                              "bitis": bitis.isoformat(), "sahip": sahip})
    return o


def momentum(sahip: str, bugun: date, pencere_ay: int = 12,
             olgunluk_ay: int = VARSAYILAN_OLGUNLUK_AY, acan=None) -> Olcum:
    """Iki es uzunlukta olgun pencerenin patent sayisi oranini olcer.

    deger > 1  -> son olgun donemde basvuru sayisi artmis
    deger = 1  -> degismemis
    deger < 1  -> azalmis

    Onceki pencere 0 ise oran tanimsizdir; bolme yapilmaz, OLCULEMEDI doner.
    """
    if pencere_ay <= 0:
        return Olcum(None, OLCULEMEDI, gerekce="pencere_ay pozitif olmali")
    if olgunluk_ay < 0:
        return Olcum(None, OLCULEMEDI, gerekce="olgunluk_ay negatif olamaz")

    bitis = veri_bitis_tarihi(bugun, olgunluk_ay)
    orta = _ay_ekle(bitis, -pencere_ay)
    basi = _ay_ekle(orta, -pencere_ay)

    son = pencere_sayisi(sahip, orta, bitis, acan=acan)
    if not son.var_mi:
        return Olcum(None, OLCULEMEDI,
                     gerekce=f"son pencere olculemedi: {son.gerekce}",
                     ayrinti={"veri_bitis_tarihi": bitis.isoformat()})
    onceki = pencere_sayisi(sahip, basi, orta, acan=acan)
    if not onceki.var_mi:
        return Olcum(None, OLCULEMEDI,
                     gerekce=f"onceki pencere olculemedi: {onceki.gerekce}",
                     ayrinti={"veri_bitis_tarihi": bitis.isoformat()})

    ayrinti = {
        "sahip": sahip,
        "son_pencere": [orta.isoformat(), bitis.isoformat()],
        "son_adet": son.deger,
        "onceki_pencere": [basi.isoformat(), orta.isoformat()],
        "onceki_adet": onceki.deger,
        "veri_bitis_tarihi": bitis.isoformat(),
        "olgunluk_ay": olgunluk_ay,
        "gecikme_notu": (f"Yayin gecikmesi nedeniyle {bitis.isoformat()} "
                         f"sonrasina BAKILMAMISTIR; bu sinyal dogasi geregi "
                         f"{olgunluk_ay} ay gecikmelidir."),
        "kaynak_kirilgan": True,
    }
    if onceki.deger == 0:
        return Olcum(None, OLCULEMEDI,
                     gerekce=("onceki pencerede patent yok; oran tanimsiz "
                              "(sifira bolme yapilmadi)"),
                     ayrinti=ayrinti)
    return Olcum(son.deger / onceki.deger, OLCULDU, ayrinti=ayrinti)
