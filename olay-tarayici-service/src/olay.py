"""
OLAY TESPITI — yalnizca RESMI dosyalama ve kurum yayinlarindan.

DIL KURALI: bu modul hicbir kosulda yon iddiasi uretmez. Cikti "su olay
tespit edildi, kaynagi su" bicimindedir. 'al', 'sat', 'firsat', 'acele'
gibi ifadeler kullanilmaz; onem sirasi bir TAVSIYE degil, olayin
duzenleyici siniflandirmasidir.

ZAMAN DAMGASI NOTU (24.08.2026'da OLCULDU):
data.sec.gov'un acceptanceDateTime alani 'Z' (UTC) ekiyle geliyor ve
GERCEKTEN UTC. Kanit: EDGAR'in 17:30 ET kesim kurali — rakamlar ET olsa
17:38 ve 17:51'de kabul edilen 8-K'larin filingDate'i ERTESI GUNE
kaymaliydi; olculdu, kaymamis. Buna karsilik getcurrent RSS ayni
rakamlari '-04:00' etiketiyle veriyor, yani RSS'in etiketi yaniltici.
Bu, RSS yerine data.sec.gov'u secmenin ikinci gerekcesidir.
"""
import re
from datetime import datetime, timezone

# 8-K Item kodlari — SEC'in resmi siniflandirmasi.
# "onem" alani bir YATIRIM TAVSIYESI DEGILDIR; yalnizca bildirimde
# siralama icin kullanilan, duzenleyici tanima dayali bir etikettir.
ONEMLI_ITEMLAR = {
    "1.01": ("Onemli bir sozlesmeye giris", "yuksek"),
    "1.02": ("Onemli bir sozlesmenin sona ermesi", "yuksek"),
    "1.03": ("Iflas ya da alacakli yonetimi", "yuksek"),
    "2.01": ("Varlik edinimi ya da elden cikarmasi", "yuksek"),
    "2.02": ("Faaliyet sonuclarinin aciklanmasi", "yuksek"),
    "2.03": ("Dogrudan finansal yukumluluk dogmasi", "orta"),
    "2.04": ("Yukumlulugun hizlandirilmasi ya da artmasi", "yuksek"),
    "2.05": ("Elden cikarma maliyetleri karari", "orta"),
    "2.06": ("Onemli deger dususu", "yuksek"),
    "3.01": ("Kotasyon kurallarina uymama / kottan cikarma bildirimi", "yuksek"),
    "4.01": ("Bagimsiz denetcinin degismesi", "yuksek"),
    "4.02": ("Onceki finansal tablolara guvenilemeyecegi", "yuksek"),
    "5.01": ("Kontrol degisikligi", "yuksek"),
    "5.02": ("Yonetici/yonetim kurulu uyesi ayrilmasi ya da atanmasi", "orta"),
    "5.03": ("Esas sozlesme ya da mali yil degisikligi", "dusuk"),
    "7.01": ("Duzenleme FD kapsaminda aciklama", "dusuk"),
    "8.01": ("Diger onemli olaylar", "dusuk"),
    "9.01": ("Finansal tablolar ve ekler", "dusuk"),
}

ONEM_SIRASI = {"yuksek": 3, "orta": 2, "dusuk": 1}


def _utc_ayristir(s: str):
    """data.sec.gov 'Z' ekli UTC verir (yukaridaki nota bakiniz)."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def sekiz_k_olaylari(gonderim: dict, azami_gun: int = 3, azami_adet: int = 5) -> list:
    """
    data.sec.gov gonderim JSON'undan son 8-K olaylarini cikarir.

    Item kodlari SEC'in KENDI yapili 'items' alanindan okunur; HTML
    ayristirmasi YAPILMAZ (daha az kirilgan ve daha az istek).
    """
    r = (gonderim.get("filings") or {}).get("recent") or {}
    formlar = r.get("form") or []
    itemlar = r.get("items") or [""] * len(formlar)
    simdi = datetime.now(timezone.utc)
    cikti = []

    for i, form in enumerate(formlar):
        if form != "8-K":
            continue
        kabul = _utc_ayristir(r.get("acceptanceDateTime", [None] * len(formlar))[i])
        if kabul is None:
            continue
        yas_saat = (simdi - kabul).total_seconds() / 3600.0
        if yas_saat > azami_gun * 24:
            continue

        kodlar = [k.strip() for k in (itemlar[i] or "").split(",") if k.strip()]
        tanimli = [(k, *ONEMLI_ITEMLAR[k]) for k in kodlar if k in ONEMLI_ITEMLAR]
        if not tanimli:
            continue
        en_yuksek = max(tanimli, key=lambda t: ONEM_SIRASI[t[2]])

        cikti.append({
            "tur": "sec_8k",
            "sirket": gonderim.get("name"),
            "cik": gonderim.get("cik"),
            "borsa_kodlari": gonderim.get("tickers") or [],
            "dosyalama_tarihi": r.get("filingDate", [None] * len(formlar))[i],
            "kabul_zamani_utc": r.get("acceptanceDateTime", [None] * len(formlar))[i],
            "yas_saat": round(yas_saat, 2),
            "item_kodlari": kodlar,
            "item_aciklamalari": [{"kod": k, "aciklama": a} for k, a, _ in tanimli],
            "duzenleyici_onem": en_yuksek[2],
            "erisim_numarasi": r.get("accessionNumber", [None] * len(formlar))[i],
            "kaynak": "SEC EDGAR (data.sec.gov) — resmi duzenleyici dosyalama",
            "kaynak_turu": "birincil_duzenleyici",
        })
        if len(cikti) >= azami_adet:
            break
    return cikti


_BASLIK = re.compile(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", re.S)
_TARIH = re.compile(r"<(?:pubDate|updated|dc:date)>(.*?)</(?:pubDate|updated|dc:date)>")


def akis_olaylari(xml: str, kimlik: str, kurum: str, azami: int = 5) -> list:
    """Kamu kurumu RSS/Atom akisindan yayin basliklari."""
    basliklar = [re.sub(r"\s+", " ", b).strip() for b in _BASLIK.findall(xml)]
    tarihler = _TARIH.findall(xml)
    if basliklar:
        basliklar = basliklar[1:]      # ilk <title> akisin kendi adi
    return [
        {
            "tur": "kurum_yayini",
            "kurum": kurum,
            "baslik": b,
            "yayin_zamani": tarihler[i] if i < len(tarihler) else None,
            "kaynak": f"{kurum} resmi yayin akisi",
            "kaynak_turu": "birincil_kamu_kurumu",
            "kaynak_kimligi": kimlik,
        }
        for i, b in enumerate(basliklar[:azami])
    ]
