"""Y3 guvenlik filtresi: AL/SAT/pozisyon tavsiyesi iceren metni tespit eder.

Prompt seviyesindeki talimat (vane_istemci.TARAMA_PROMPT_SABLONU) tek
basina yeterli DEGIL - canli testte Vane'in ham yaniti "olumlu sinyaller
vermektedir" gibi tavsiye-benzeri dil icerdigi dogrudan gozlemlendi.
Bu yuzden ikinci, kod-seviyeli bir savunma katmani gerekir.

Fail-loud: tetiklenen bir yanit SESSIZCE bos donmez (Y5) - yerine
tetiklendigi acikca isaretlenmis, tavsiye icermeyen sabit bir mesajla
degistirilir.
"""
import re

YASAKLI_KALIPLAR = [
    r"\bal[ıi]n\b", r"\bsat[ıi]n\s+al", r"\bsat[ıi]n\b", r"\bsat\b",
    r"\btut\b", r"\bbekle[a-zçğıöşü]*\b", r"\bpozisyon\b", r"\bhedef\s+fiyat",
    r"yat[ıi]r[ıi]m\s+tavsiye", r"yat[ıi]r[ıi]m\s+perspektif",
    r"olumlu\s+sinyal", r"olumsuz\s+sinyal", r"y[üu]kseli[şs]\s+potansiyel",
    r"d[üu][şs][üu][şs]\s+potansiyel", r"portf[öo]y\s+[öo]neri",
    r"\bal[ıi][şs]\s+f[ıi]rsat", r"\bsat[ıi][şs]\s+f[ıi]rsat",
    r"\bbuy\b", r"\bsell\b", r"\bhold\b", r"price\s+target",
    r"overweight", r"underweight", r"\brating\b",
]

_DERLENMIS = [re.compile(p, re.IGNORECASE) for p in YASAKLI_KALIPLAR]

YEDEK_MESAJ = (
    "Bu sembol icin bugun gundemde otomatik tarama tarafindan tespit "
    "edilen bir gelisme var, ancak sistem metinde tavsiye niteliginde "
    "ifade tespit ettigi icin ayrinti burada paylasilamiyor. Lutfen "
    "bagimsiz kaynaklardan kendiniz teyit edin."
)

FERAGAT_METNI = (
    "Bu bir yatirim tavsiyesi degildir; yalnizca farkindalik amacli "
    "otomatik bir bilgilendirmedir."
)


def denetle(metin: str) -> dict:
    """Metni tavsiye-benzeri dil icin tarar.

    Donen: {"tetiklendi": bool, "eslesen_kaliplar": list[str], "guvenli_metin": str}
    """
    eslesenler = [p.pattern for p in _DERLENMIS if p.search(metin)]
    if eslesenler:
        return {
            "tetiklendi": True,
            "eslesen_kaliplar": eslesenler,
            "guvenli_metin": f"{YEDEK_MESAJ}\n\n{FERAGAT_METNI}",
        }
    return {
        "tetiklendi": False,
        "eslesen_kaliplar": [],
        "guvenli_metin": f"{metin.strip()}\n\n{FERAGAT_METNI}",
    }
