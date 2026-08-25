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


# ===========================================================================
# KELIME SINIRI ZORUNLU (25.08.2026) — "EKLE, BEKLE'nin icinde" hatasi
# ===========================================================================
# ESKI HAL: `code in text` duz ALT DIZE aramasiydi. "EKLE" dizgisi "BEKLE"
# kelimesinin ICINDE gectigi icin, karari BEKLE olan HER metin
# check_decision_code'dan ['EKLE', 'BEKLE'] olarak donuyordu:
#     check_decision_code("Karar: BEKLE") -> ['EKLE', 'BEKLE']
# constitution_check bunu "Birden fazla karar kodu bulundu, tekile
# indirilmeli" diye isaretliyordu. Yani dort gecerli koddan BIRI
# (BEKLE) secildiginde metin HER ZAMAN anayasa kontrolunden dusuyor,
# cascade.py:218-240'taki hedefli yeniden deneme dongusu bosuna iki kez
# LLM cagiriyor ve sonucta cascade_meta.constitution_check kalici olarak
# clear=False raporluyordu — yani denetim sinyali anlamsizlasmisti.
#
# Kelime siniri (\b) bu cakismayi kaldirir: "\bEKLE\b" ifadesi "BEKLE"
# icindeki EKLE'ye ESLESMEZ (onundeki B bir kelime karakteri, sinir yok).
# Ayrica "EKLEME"/"EKLENEBILIR" gibi turemis kelimeler de artik yanlislikla
# karar kodu sayilmaz.
_KOD_DESENLERI = {
    kod: re.compile(r"\b" + re.escape(kod) + r"\b")
    for kod in ALLOWED_DECISION_CODES
}


def check_decision_code(text: str):
    """Metinde gecen izinli karar kodlarini dondurur (kelime siniriyla)."""
    return [kod for kod, desen in _KOD_DESENLERI.items() if desen.search(text)]


# "KISA VADE: X" / "UZUN VADE: Y" bildirimlerini yakalayan desen.
# check_timeframe_codes ile AYNI deseni kullanir ki iki fonksiyon zamanla
# birbirinden kaymasin.
_VADE_BILDIRIMI = re.compile(
    r"(KISA|UZUN)\s*VADE[:\s]*\**\s*(EKLE|TUT|BEKLE|DIKKAT ET)",
    re.IGNORECASE,
)


def _vade_bildirimlerini_ayikla(text: str) -> str:
    """Vade bildirimlerini metinden cikarir; geriye kalani denetlenir."""
    return _VADE_BILDIRIMI.sub(" ", text)


# ===========================================================================
# YASAL UYARI KENDI KONTROLUNU DUSURUYORDU (25.08.2026'da GERCEK CIKTIYLA
# olculdu) — bu, uc kusurun EN BASKIN olani
# ===========================================================================
# LEGAL_DISCLAIMER metninin kendisi su cumleyi iceriyor:
#     "Tum karar kodlari (EKLE/TUT/BEKLE/DIKKAT ET) kantitatif veri
#      durumunu ifade eder, islem emri degildir."
# ensure_disclaimer() bu metni cikitinin BASINA VE SONUNA ekliyor. Sonuc:
# constitution_check tum metni tarayinca DORT kodu birden buluyor ve
# "Birden fazla karar kodu bulundu" diyor — analiz govdesinde tek ve net
# bir "Karar: **BEKLE**" olmasina ragmen.
#
# GERCEK OLCUM (24.08.2026 kaskad ciktilari, 5 kosumun 5'i):
#     once/AAPL, once/MSFT, once/NVDA, sonra/AAPL, sonra/NVDA
#     -> hepsinde check_decision_code = ['EKLE','TUT','BEKLE','DIKKAT ET']
#     -> hepsinde constitution_check.clear = False
#     -> hepsinde cascade_meta.retry_count = 2 (dongu HER ZAMAN tukeniyor)
# Yani yeniden deneme dongusu ASLA basarili olamiyordu: metinde uyari
# durdukca kontrol matematiksel olarak gecilemezdi. Her kaskad, hicbir
# gercek ihlal olmadigi halde IKI fazladan LLM cagrisi yakiyordu.
#
# DUZELTME: denetim yapilmadan once BIZIM eklediğimiz sabit uyari metni
# cikarilir. Bu bir zayiflatma DEGILDIR: uyari bizim boilerplate'imiz,
# modelin karari degil. Modelin gercekten urettiği metinde birden fazla
# kod kalirsa hala ihlal sayilir.
def _uyariyi_ayikla(text: str) -> str:
    """Kendi eklediğimiz yasal uyariyi denetim disi birakir."""
    return text.replace(LEGAL_DISCLAIMER, " ")


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
    # Kendi yasal uyarimiz denetim disi (bkz. _uyariyi_ayikla notu).
    denetlenecek = _uyariyi_ayikla(text)

    banned = check_banned_words(denetlenecek)
    if banned:
        issues.append(f"Yasakli kelime(ler) bulundu: {', '.join(banned)}")

    # =======================================================================
    # VADE FORMATI ILE "TEK KOD" KURALININ CELISKISI (25.08.2026'da olculdu)
    # =======================================================================
    # output_guard.sema_talimati_vadeli() metne IKI kod yazdiriyor
    # ("KISA VADE: X" ve "UZUN VADE: Y") ve kendi metninde bunlarin FARKLI
    # olabilecegini "normal ve beklenen bir durumdur" diye yaziyor.
    # Ancak buradaki eski kural her ek kodu ihlal sayiyordu. Olculen sonuc:
    #     "KISA VADE: DIKKAT ET ... UZUN VADE: EKLE"
    #        -> constitution_check.clear = False
    #        -> check_timeframe_codes.ikisi_de_var = True
    #        -> cascade.py'nin birlesik kosulu HICBIR ZAMAN saglanamiyor
    # Yani tasarlanan ve tesvik edilen ciktinin kendisi kontrolu gecemiyordu;
    # kaskad her seferinde iki bosa yeniden deneme yakip clear=False
    # raporluyordu.
    #
    # DUZELTME: vade formati kullanildiginda iki vade kodu MESRUDUR. Kural
    # ZAYIFLATILMIYOR — belirsizlige karsi koruma duruyor: vade bildirimleri
    # metinden cikarildiktan SONRA geriye birden fazla BASIBOS kod kalirsa
    # bu hala ihlaldir. Boylece "EKLE sinyali guclenir ama BEKLE de olabilir"
    # gibi ikircikli metinler yakalanmaya devam eder.
    tf = check_timeframe_codes(denetlenecek)
    if tf["ikisi_de_var"]:
        artik_kodlar = check_decision_code(_vade_bildirimlerini_ayikla(denetlenecek))
        if len(artik_kodlar) > 1:
            issues.append(
                "Vade bildirimleri disinda birden fazla basibos karar kodu "
                f"bulundu, tekile indirilmeli: {artik_kodlar}"
            )
    else:
        codes = check_decision_code(denetlenecek)
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
