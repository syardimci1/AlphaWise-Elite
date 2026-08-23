"""
λ = 0 ZORUNLU KISIT — kod seviyesinde engelleme.

Deney 1 (23.08.2026) olctu: 25 mega-cap x 3,57 yilda yalnizca 32 acik piyasa
ALIMI var ve bunun 29'u tek bir hissede (BAC). Ornek-disi test bolumu ~12
gozlem olurdu; God Mode esigi 1.000+ gozlem istiyor. Yani bu evrende yon
kalibrasyonu MATEMATIKSEL OLARAK MUMKUN DEGIL.

Bu modul o kisiti bir YORUM olarak degil, CALISAN BIR ENGEL olarak uygular:
servisten cikan HER yanit `dogrula()` fonksiyonundan gecer. Yanitta bir yon
alani ya da yon/emir bildiren bir ifade bulunursa istisna firlatilir ve yanit
kullaniciya ULASMAZ. Yani ileride biri yanlislikla (ya da bilerek) bir yon
kodu eklerse, servis sessizce yanlis is yapmak yerine GURULTULU sekilde
kirilir.

Ayrica CLAUDE.md dil kurali: kesinlik/emir bildiren dil yasak.
DIKKAT: "alim", "satis", "acik piyasa alimi" gibi OLGUSAL isim halleri
serbesttir — bu servisin isi zaten onlari raporlamaktir. Yasaklanan sey
EMIR ve TAHMIN kipleridir.
"""
import re

# Bu deger degistirilemez. Yukseltilmesi ancak Deney 1 TASARIM belgesindeki
# kalibrasyon yolundan (evren 6.783 hisseye cikarilip God Mode disiplininde
# test edilerek) gecebilir.
LAMBDA = 0.0

# Yanitta ASLA bulunamayacak alan adlari (kucuk harfe indirgenerek aranir)
YASAK_ANAHTARLAR = frozenset({
    "yon", "yon_kodu", "yon_olasiligi", "yon_skoru", "yon_sinyali",
    "karar", "karar_kodu", "sinyal_yonu", "tavsiye", "oneri_yon",
    "hedef_fiyat", "alim_sinyali", "satim_sinyali", "skor_yon",
    "beklenen_getiri", "olasilik_yukari", "probability_up",
    "direction", "signal_direction", "recommendation", "target_price",
})

# Emir/kesinlik/tahmin kipleri. Kelime sinirli; olgusal isim halleri
# ("alim", "satis", "alimlar") bilerek DISARIDA birakildi.
YASAK_IFADELER = [
    (re.compile(r"\b(EKLE|TUT|BEKLE)\b"), "God Mode/MAA karar kodu"),
    (re.compile(r"\bD[İI]KKAT\s+ET\b", re.I), "MAA karar kodu"),
    # NOT: gruplama parantezi ZORUNLU. "al[ıi]n[ıi]z?" yazilirsa yalnizca
    # "alınız" yakalanir, duz "ALIN" KACAR (23.08.2026'da birim testi bunu
    # yakaladi). Dogru bicim: govde + istege bagli "-ız" eki.
    (re.compile(r"\bal[ıi]n(?:[ıi]z)?\b", re.I), "emir kipi (alin/aliniz)"),
    (re.compile(r"\bsat[ıi]n\s+al", re.I), "emir kipi (satin al)"),
    (re.compile(r"\bsat[ıi]n(?:[ıi]z)?\b", re.I), "emir kipi (satin/satiniz)"),
    (re.compile(r"\by[üu]kselecek\b", re.I), "kesin gelecek iddiasi"),
    (re.compile(r"\bd[üu][şs]ecek\b", re.I), "kesin gelecek iddiasi"),
    (re.compile(r"\byukar[ıi]\s+gidecek\b", re.I), "kesin gelecek iddiasi"),
    (re.compile(r"\bgaranti\b", re.I), "kesinlik ifadesi"),
    (re.compile(r"\bkesinlikle\b", re.I), "kesinlik ifadesi"),
    (re.compile(r"\bmutlaka\b", re.I), "kesinlik ifadesi"),
    (re.compile(r"\bfiyat[ıi]ndan\s+gir", re.I), "emir kipi (giris fiyati)"),
]


class LambdaSifirIhlali(Exception):
    """Yanit λ=0 kisitini ihlal ediyor — kullaniciya gonderilemez."""


def _anahtar_tara(nesne, yol=""):
    if isinstance(nesne, dict):
        for k, v in nesne.items():
            ad = str(k).lower()
            if ad in YASAK_ANAHTARLAR:
                raise LambdaSifirIhlali(
                    f"YASAK ALAN: '{yol}{k}' — bu servis yon kodu/yon olasiligi "
                    f"uretemez (lambda=0, Deney 1: 3,57 yilda 32 acik piyasa alimi)")
            _anahtar_tara(v, f"{yol}{k}.")
    elif isinstance(nesne, (list, tuple)):
        for i, v in enumerate(nesne):
            _anahtar_tara(v, f"{yol}[{i}].")


def _metin_tara(nesne, yol=""):
    if isinstance(nesne, str):
        for desen, aciklama in YASAK_IFADELER:
            m = desen.search(nesne)
            if m:
                raise LambdaSifirIhlali(
                    f"YASAK IFADE: '{yol}' icinde \"{m.group(0)}\" ({aciklama}); "
                    f"CLAUDE.md dil kurali ve lambda=0 kisiti geregi engellendi")
    elif isinstance(nesne, dict):
        for k, v in nesne.items():
            _metin_tara(v, f"{yol}{k}.")
    elif isinstance(nesne, (list, tuple)):
        for i, v in enumerate(nesne):
            _metin_tara(v, f"{yol}[{i}].")


def dogrula(payload):
    """Yaniti λ=0 kisitina gore denetler. Ihlal varsa LambdaSifirIhlali firlatir.

    Servisin HER endpoint'i bu fonksiyondan gecmek ZORUNDADIR.
    """
    if LAMBDA != 0.0:
        raise LambdaSifirIhlali(
            f"LAMBDA={LAMBDA}; bu servis icin kalibrasyon gecerli degil, "
            f"lambda 0 disinda bir deger alamaz")
    _anahtar_tara(payload)
    _metin_tara(payload)
    return payload
