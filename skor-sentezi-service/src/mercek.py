"""
Mercekler — ayni olcume farkli yatirim felsefelerinden bakmak (Madde 31).

EN ONEMLI KURAL: MERCEK OLCUMU DEGISTIRMEZ
==========================================
Bir mercek YALNIZCA SIRALAMA ve VURGU degistirir. Sunlari YAPMAZ:
  * Eksen puanlarini yeniden agirliklandirmaz.
  * Genel puani degistirmez.
  * Hicbir ekseni GIZLEMEZ.
  * Karar kodu uretmez.

Neden bu kadar kati: ayni veriden mercege gore FARKLI SAYILAR uretmek,
kullaniciya "istedigin cevabi veren mercegi sec" demek olurdu. Bu, olcumu
sunuma tabi kilar ve sistemin butun guvenilirligini bitirir. Bu depoda
zaten kalibre edilmis bir agirlik seti YOK (bkz. sentez.py: "uydurulmus
agirliklar sonuca sahte kesinlik katardi") — mercek bunu arka kapidan
geri getiremez.

Mercek yalnizca sunu soyler: "senin felsefene gore ONCE su olcume bak."
Ve durustlugun bedelini de oder: her mercek, NEYI SOYLEYEMEDIGINI de yazar.
"""
from __future__ import annotations

# Eksen anahtarlari sentez.py ile AYNI olmali; ayrisma testle kilitlenir.
TARAFSIZ = "tarafsiz"

MERCEKLER = [
    {
        "anahtar": TARAFSIZ,
        "ad": "Tarafsız",
        "aciklama": "Eksenler yayımlanma sırasında; hiçbir vurgu yapılmaz.",
        "sira": ["finansal_saglik", "kazanc_kalitesi", "temel_guc",
                 "degerleme", "temettu"],
        "one_cikan": [],
        "gerekce": {},
        "soyleyemedikleri": [
            "Bu görünüm bir yatırım felsefesi önermez; ölçümleri olduğu gibi sıralar.",
        ],
    },
    {
        "anahtar": "temettu_odakli",
        "ad": "Temettü Odaklı",
        "aciklama": "Düzenli nakit akışını önceleyen yatırımcı için.",
        "sira": ["temettu", "finansal_saglik", "kazanc_kalitesi",
                 "temel_guc", "degerleme"],
        "one_cikan": ["temettu", "finansal_saglik"],
        "gerekce": {
            "temettu": "Ödeme oranı ve serbest nakit akışı kapsamı, temettünün "
                       "sürdürülebilirliğini doğrudan ölçer.",
            "finansal_saglik": "Borç yükü artan bir şirkette temettü, kesilmesi "
                               "en kolay kalemdir.",
            "kazanc_kalitesi": "Temettüyü besleyen kârın muhasebe kalitesi.",
        },
        "soyleyemedikleri": [
            "Temettü VERİMİ (yüzde) bu eksende ölçülmez; ölçülen dayanıklılıktır.",
            "Temettü ödemeyen bir şirket 'kötü' değildir; o eksen UYGULANAMAZ döner.",
            "Gelecekteki temettü kararları hakkında hiçbir şey söylemez.",
        ],
    },
    {
        "anahtar": "deger_odakli",
        "ad": "Değer Odaklı",
        "aciklama": "Fiyat ile içsel değer arasındaki farkı önceleyen yatırımcı için.",
        "sira": ["degerleme", "finansal_saglik", "kazanc_kalitesi",
                 "temel_guc", "temettu"],
        "one_cikan": ["degerleme", "kazanc_kalitesi"],
        "gerekce": {
            "degerleme": "İçsel değerin fiyata oranı, bu felsefenin merkezindeki "
                         "ölçüdür.",
            "kazanc_kalitesi": "Ucuz görünen bir şirketin kârı gerçek mi — "
                               "değer tuzağını ayırt eden ölçü.",
            "finansal_saglik": "Ucuzluk, iflas riskinden geliyor olabilir.",
        },
        "soyleyemedikleri": [
            "Değerleme ekseni beş eksen içinde VARSAYIMA EN DUYARLI olanıdır; "
            "tek bir sayı olarak okunmamalıdır (duyarlılık bandına bakın).",
            "'Ucuz' olması yükseleceği anlamına gelmez.",
        ],
    },
    {
        "anahtar": "kalite_odakli",
        "ad": "Kalite Odaklı",
        "aciklama": "İşin temel sağlamlığını önceleyen yatırımcı için.",
        "sira": ["temel_guc", "kazanc_kalitesi", "finansal_saglik",
                 "temettu", "degerleme"],
        "one_cikan": ["temel_guc", "kazanc_kalitesi"],
        "gerekce": {
            "temel_guc": "Kârlılık, kaldıraç ve verimlilikteki dokuz ikili "
                         "ölçüt, işin yılına göre iyileşip iyileşmediğini gösterir.",
            "kazanc_kalitesi": "Raporlanan kârın muhasebe kalemleriyle şişirilip "
                               "şişirilmediği.",
        },
        "soyleyemedikleri": [
            "Kaliteli bir şirket pahalı olabilir; bu mercek fiyat sormaz.",
            "Piotroski F-Score yıllık değişime bakar; tek yıllık bir fotoğraf değildir.",
        ],
    },
    {
        "anahtar": "risk_odakli",
        "ad": "Risk Odaklı",
        "aciklama": "Sermaye kaybı riskini önceleyen yatırımcı için.",
        "sira": ["finansal_saglik", "kazanc_kalitesi", "temel_guc",
                 "temettu", "degerleme"],
        "one_cikan": ["finansal_saglik", "kazanc_kalitesi"],
        "gerekce": {
            "finansal_saglik": "Altman Z, iflas riskini doğrudan hedefleyen "
                               "yayımlanmış ölçüttür.",
            "kazanc_kalitesi": "Muhasebe manipülasyonu, riskin en geç fark "
                               "edilen biçimidir.",
        },
        "soyleyemedikleri": [
            "Bu eksenler ŞİRKET riskini ölçer; PİYASA riskini (düşüş dayanıklılığı) "
            "ölçmez — onun için kriz stres testine bakın.",
            "Altman Z finansal kurumlara UYGULANMAZ; bankalarda bu eksen boş kalır.",
        ],
    },
]

MERCEK_HARITASI = {m["anahtar"]: m for m in MERCEKLER}


def mercek_bul(anahtar):
    """Bilinmeyen anahtar SESSIZCE tarafsiza dusmez; bunu bildirir."""
    # ONCE kirp, SONRA varsayilana dus: "   " gibi yalnizca bosluk iceren bir
    # girdi Python'da DOGRU (truthy) oldugu icin, kirpma sonraya birakilirsa
    # bos dizge "bilinmeyen mercek" sayilip gereksiz uyari uretiyordu.
    a = (anahtar or "").strip().lower() or TARAFSIZ
    if a in MERCEK_HARITASI:
        return MERCEK_HARITASI[a], None
    return (MERCEK_HARITASI[TARAFSIZ],
            f"Bilinmeyen mercek '{anahtar}'; tarafsız görünüm kullanıldı.")


def uygula(sentez_sonucu: dict, anahtar: str = TARAFSIZ) -> dict:
    """Eksenleri mercege gore SIRALAR ve vurgu/gerekce ekler.

    Puanlara, genel puana ve duruma DOKUNMAZ. Hicbir eksen atilmaz:
    girdideki eksen sayisi ile ciktidaki AYNI olmak zorundadir.
    """
    mercek, uyari = mercek_bul(anahtar)
    eksenler = list(sentez_sonucu.get("eksenler", []))
    sira = {k: i for i, k in enumerate(mercek["sira"])}

    # Mercekte adi gecmeyen bir eksen SONA konur ama ATILMAZ.
    duzen = sorted(eksenler, key=lambda e: (sira.get(e.get("anahtar"), 999),
                                            e.get("anahtar", "")))
    zenginlestirilmis = []
    for e in duzen:
        a = e.get("anahtar")
        zenginlestirilmis.append({
            **e,
            "one_cikan": a in mercek["one_cikan"],
            "mercek_gerekcesi": mercek["gerekce"].get(a, ""),
        })

    return {
        **sentez_sonucu,
        "eksenler": zenginlestirilmis,
        "mercek": {
            "anahtar": mercek["anahtar"], "ad": mercek["ad"],
            "aciklama": mercek["aciklama"],
            "soyleyemedikleri": mercek["soyleyemedikleri"],
            "uyari": uyari,
            "degismezlik_notu": (
                "Mercek yalnızca SIRALAMA ve VURGU değiştirir. Puanlar, genel "
                "puan ve ölçüm durumları merceğe göre DEĞİŞMEZ; hiçbir eksen "
                "gizlenmez."),
        },
    }
