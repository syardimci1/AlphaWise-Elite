"""
ALPHAWISE - Retry Yolu Gercek Testi (15.08.2026)
Amac: cascade.py'deki retry mekanizmasinin, BILEREK ihlalli bir metni
gercekten duzeltip duzeltemedigini olcmek. Bugune kadar retry_count=0
oldugu icin bu yol hic test edilmemisti.
"""
import sys, os, asyncio, time
sys.path.insert(0, os.path.dirname(__file__))

from constitution import constitution_check
from cascade import _call_with_fallback, MASTER_MODELS
from output_guard import sema_talimati

# --- Bilerek IHLALLI metinler (gercek hata desenlerimizden) ---
VAKALAR = [
    ("coklu karar kodu", """## SADE OZET
NVDA icin degerlendirme: mevcut gorunum EKLE yonunde guclu.
Ancak kisa vadeli belirsizlik nedeniyle BEKLE de dusunulebilir.
KARAR: EKLE"""),
    ("yasakli kelime", """## SADE OZET
TSM hissesini al diyoruz, guclu bir firsat var.
KARAR: TUT"""),
    ("gecersiz karar kodu", """## SADE OZET
AAPL icin piyasa takip edilmeli.
KARAR: IZLE"""),
]


async def test_vaka(ad, metin):
    print(f"\n{'='*60}", flush=True)
    print(f"VAKA: {ad}", flush=True)
    ilk = constitution_check(metin)
    print(f"  Baslangic : clear={ilk['clear']} | {ilk['issues']}", flush=True)
    if ilk["clear"]:
        print(f"  ATLANDI (metin zaten temiz - test gecersiz)", flush=True)
        return None

    final, check, deneme = metin, ilk, 0
    t0 = time.time()
    while not check["clear"] and deneme < 2:
        deneme += 1
        fix_prompt = (
            "Asagidaki metin Anayasa v4.4 kontrolunu GECEMEDI.\n"
            f"TESPIT EDILEN SORUNLAR: {', '.join(check['issues'])}\n"
            f"METIN: {final}\n"
            "Gorevin: SADECE bu spesifik sorunlari duzelt, metnin geri kalanini koru. "
            "KARAR KODU KURALI (EN ONEMLI): Metnin TAMAMINDA yalnizca TEK bir karar kodu "
            "gecmeli. EKLE / TUT / BEKLE / DIKKAT ET kodlarindan SADECE birini sec ve "
            "digerlerini metnin HICBIR yerinde - ornek, aciklama, senaryo dahil - YAZMA. "
            "al/sat/tavsiye/koru/firsat/ralli/roket kelimelerini KESINLIKLE kullanma."
            + sema_talimati()
        )
        yeni, model = await _call_with_fallback(MASTER_MODELS, fix_prompt)
        if yeni:
            final = yeni
            check = constitution_check(final)
            print(f"  Deneme {deneme}: clear={check['clear']} | {check['issues'] or 'TEMIZ'}", flush=True)
        else:
            print(f"  Deneme {deneme}: LLM yanit vermedi", flush=True)
            break

    sure = time.time() - t0
    sonuc = "BASARILI" if check["clear"] else "BASARISIZ"
    print(f"  SONUC     : {sonuc} ({deneme} deneme, {sure:.1f}sn)", flush=True)
    return check["clear"], deneme


async def main():
    print("RETRY YOLU GERCEK TESTI", flush=True)
    sonuclar = []
    for ad, metin in VAKALAR:
        r = await test_vaka(ad, metin)
        if r:
            sonuclar.append((ad, *r))

    print(f"\n{'='*60}", flush=True)
    print("OZET", flush=True)
    basarili = sum(1 for _, ok, _ in sonuclar if ok)
    for ad, ok, d in sonuclar:
        print(f"  [{'OK  ' if ok else 'HATA'}] {ad}: {d} denemede {'duzeltildi' if ok else 'DUZELTILEMEDI'}", flush=True)
    print(f"\n  Basari orani: {basarili}/{len(sonuclar)}", flush=True)
    if basarili < len(sonuclar):
        print("  NOT: duzeltilemeyen vakalar icin sema-zorlama (Outlines) sart", flush=True)

asyncio.run(main())
