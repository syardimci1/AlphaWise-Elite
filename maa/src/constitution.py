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


# ===== VADE-AYRIMLI KARAR SEMASI (15.08.2026) =====
# AL/SAT gibi emir-bildiren kelimeler HALA YASAK - sadece mevcut 4 koda
# (EKLE/TUT/BEKLE/DIKKAT ET) vade boyutu ekleniyor. Yasal sinir degismiyor.
KISA_VADE_KODLARI = ALLOWED_DECISION_CODES  # ayni 4 kod
UZUN_VADE_KODLARI = ALLOWED_DECISION_CODES  # ayni 4 kod


def check_timeframe_codes(text: str):
    """Kisa ve uzun vade icin AYRI AYRI karar kodu var mi, ikisi de gecerli mi kontrol eder."""
    import re
    kisa_match = re.search(r"KISA\s*VADE[:\s]*\**\s*(EKLE|TUT|BEKLE|DIKKAT ET)", text, re.IGNORECASE)
    uzun_match = re.search(r"UZUN\s*VADE[:\s]*\**\s*(EKLE|TUT|BEKLE|DIKKAT ET)", text, re.IGNORECASE)
    return {
        "kisa_vade_kodu": kisa_match.group(1).upper() if kisa_match else None,
        "uzun_vade_kodu": uzun_match.group(1).upper() if uzun_match else None,
        "ikisi_de_var": bool(kisa_match and uzun_match),
    }
