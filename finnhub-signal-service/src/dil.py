"""
Anayasa dil denetimi — bu servise ozel UYARLAMA.

liquidity-signal-service/src/anayasa_dili.py ile ayni yasak kelime
listesini kullanir, ANCAK kritik bir farkla:

UCUNCU TARAF METNI DENETLENMEZ.
Finnhub'dan gelen haber BASLIKLARI bize ait bir tavsiye degil, disaridan
gelen HAM VERIDIR. Yasak listede 'must' ve 'should' gibi Ingilizce
kelimeler var; "Analysts say investors should watch..." gibi tamamen
normal bir baslik bu denetimden gecemezdi. Bu, gercek bir haberi
sansurlemek ya da servisi bosuna hataya dusurmek anlamina gelirdi.

Dogru ayrim: denetim BIZIM URETTIGIMIZ metinlere uygulanir
(aciklama, uyari, ozet alanlari). Ucuncu taraf basliklar 'baslik',
'kaynak', 'url' alanlarinda TASINIR ve arayuzde kaynagiyla birlikte
gosterilir — bizim degerlendirmemiz olmadigi acikca yazilir.
"""
import re

YASAK_PATTERNS = [
    r"\bal\b", r"\bsat\b", r"\bkesinlikle\b", r"\bmutlaka\b",
    r"\bgaranti\b", r"\byukari gidecek\b", r"\basagi gidecek\b",
    r"\bhemen\b", r"\bacele\b", r"\bpanik\b", r"\bfirsat\b",
    r"\bkacirma\b", r"\bkacirir\b", r"\bkacirmayin\b",
    r"\bmust\b", r"\bshould\b",
]
YASAK_RX = [re.compile(p, re.IGNORECASE) for p in YASAK_PATTERNS]

# Ucuncu taraf ham verisi tasiyan alan adlari — denetim disi.
UCUNCU_TARAF_ALANLARI = {"baslik", "kaynak", "url", "secili_basliklar"}


def metin_denetle(metin: str) -> list:
    if not isinstance(metin, str):
        return []
    return [{"patern": rx.pattern, "eslesme": m.group()}
            for rx in YASAK_RX for m in rx.finditer(metin)]


def yanit_denetle(veri) -> dict:
    """BIZIM urettigimiz metin alanlarini denetler; ucuncu taraf alanlarini ATLAR."""
    ihlaller = []

    def yuru(x, yol="", ucuncu_taraf=False):
        if isinstance(x, dict):
            for k, v in x.items():
                yuru(v, f"{yol}.{k}" if yol else k,
                     ucuncu_taraf or k in UCUNCU_TARAF_ALANLARI)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yuru(v, f"{yol}[{i}]", ucuncu_taraf)
        elif isinstance(x, str) and not ucuncu_taraf:
            for e in metin_denetle(x):
                ihlaller.append({"alan": yol, **e})

    yuru(veri)
    return {"temiz": len(ihlaller) == 0, "ihlaller": ihlaller}
