"""
ALPHAWISE Anayasasi v4.4 - koda gomulu kurallar.
Kaskadin her asamasinda (Analyst/Critic/Master) uygulanir.
"""
import re

ALLOWED_DECISION_CODES = ["EKLE", "TUT", "BEKLE", "DIKKAT ET"]

BANNED_WORDS = ["al", "sat", "tavsiye", "koru", "kar realize et", "firsat", "ralli", "roket"]

LEGAL_DISCLAIMER = (
    "**YASAL UYARI:** Bu icerik yatirim danismanligi degildir. ALPHAWISE, "
    "hicbir finansal duzenleyici kurum nezdinde kayitli yatirim danismani "
    "degildir. Sistem hicbir pozisyon acma, kapama veya azaltma talimati "
    "vermez. Tum karar kodlari (EKLE/TUT/BEKLE/DIKKAT ET) kantitatif veri "
    "durumunu ifade eder, islem emri degildir. Gecmis performans gelecegin "
    "garantisi degildir. Kararlarinizi vermeden once lisansli bir finansal "
    "danismana danisin."
)


def check_banned_words(text: str):
    """
    Metinde yasakli kelimeleri kelime-siniri (word boundary) ile arar.
    Yanlis pozitifleri onlemek icin baglam kontrolu yapar:
    "satis" gibi kelimenin icinde gecen "sat" kok halini yakalamaz,
    sadece bagimsiz kelime olarak gecen yasakli terimleri yakalar.
    """
    violations = []
    lowered = text.lower()
    for word in BANNED_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, lowered):
            violations.append(word)
    return violations


def check_decision_code(text: str):
    """Metinde gecen karar kodunun izinli 4 kodtan biri olup olmadigini kontrol eder."""
    found_codes = [code for code in ALLOWED_DECISION_CODES if code in text]
    return found_codes


def ensure_disclaimer(text: str):
    """Metnin basinda ve sonunda yasal uyari yoksa ekler."""
    if LEGAL_DISCLAIMER not in text:
        text = f"{LEGAL_DISCLAIMER}\n\n{text}\n\n{LEGAL_DISCLAIMER}"
    return text


def constitution_check(text: str):
    """
    Bir metnin Anayasa v4.4'e uygunlugunu kontrol eder.
    Donen sozluk: {"clear": bool, "issues": [...]}
    """
    issues = []
    banned = check_banned_words(text)
    if banned:
        issues.append(f"Yasakli kelime(ler) bulundu: {', '.join(banned)}")

    codes = check_decision_code(text)
    if not codes:
        issues.append("Gecerli bir karar kodu (EKLE/TUT/BEKLE/DIKKAT ET) bulunamadi")
    elif len(codes) > 1:
        issues.append(f"Birden fazla karar kodu bulundu, tekile indirilmeli: {codes}")

    return {"clear": len(issues) == 0, "issues": issues}
