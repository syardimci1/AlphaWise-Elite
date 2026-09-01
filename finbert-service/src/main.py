"""
ALPHAWISE - FinBERT Sentiment Servisi
FinGPT'nin ucretsiz, GPU gerektirmeyen alternatifi.
ProsusAI/finbert (HuggingFace, gated degil, 110M parametre, CPU'da calisir)
kullanarak finansal metin sentiment analizi yapar.

=======================================================================
TEDARIK ZINCIRI SABITLEMESI (01.09.2026 denetimi)
=======================================================================
OLCULEN RISK: bu dosya eskiden su tek satiri kullaniyordu:

    pipeline("sentiment-analysis", model="ProsusAI/finbert")

Iki sabitleme de yoktu:
  1. REVISION PIN YOK -> her indirmede HF'in o anki "main" dali alinir.
     Model deposu (kazayla ya da kotu niyetle) degistirilse sistem yeni
     dosyayi SESSIZCE yukler.
  2. BUTUNLUK DOGRULAMASI YOK -> indirilen dosyanin beklenen dosya
     oldugunu hicbir sey kontrol etmiyordu.

Ve bu, ozellikle onemli cunku bu depoda YUKLENEN DOSYA PICKLE'DIR:
"main" dalinda model.safetensors YOKTUR (resolve/main/model.safetensors
-> HTTP 404); yalnizca pytorch_model.bin vardir.

PICKLE RISKININ DURUST BUYUKLUGU (01.09.2026 supheci turu olcumu): bu
yiginda torch coktan kisitlidir - transformers.modeling_utils.load_state_dict
imzasi weights_only=True'dur ve audit hook ile olculdugunde hem indirme hem
yukleme sirasinda pickle.find_class olayi 0 cikti; config.json'da auto_map
yok. Yani "pickle tanim geregi kod calistirir" ifadesi GENEL olarak dogru
ama BU yigin icin abartilidir; keyfi kod calistirma yolu bugun acik degil.
Sabitleme yine de gereklidir, cunku asil koruma sudur: agirliklarin (ve
config/vocab'in) DEGISTIRILMEDIGINI dogrulamak. Bir modelin agirligini
sessizce degistirmek, kod calistirmadan da kararlarimizi bozar.

use_safetensors=True NEDEN COZUM DEGIL: safetensors bu depoda yalnizca
BIRLESTIRILMEMIS ucuncu taraf PR dalinda (refs/pr/29) bulunuyor. O bayrak
verildiginde transformers sessizce o dogrulanmamis dala dusuyor - yani
riski azaltmiyor, BASKA bir tedarik zinciri riskine ceviriyor. Denetimde
olculdu ve bu yol bilincli olarak REDDEDILDI.

SECILEN COZUM (a): revision pin + indirilen dosyalarin sha256 dogrulamasi.
Kendi barindirma (b) secenegi degerlendirildi ve secilmedi: ilk kopyayi
yine HF'ten alacagimiz icin tedarik zinciri riskini kaldirmiyor, ama
kalici depolama ve guncelleme sorumlulugu ekliyor.

*** SIRA KRITIK ***: dogrulama, pickle YUKLENMEDEN ONCE yapilir.
snapshot_download() dosyalari yalnizca INDIRIR (deserialize etmez);
sha256 dogrulamasi ondan sonra, from_pretrained cagrilmadan once kosar.
Once yukleyip sonra dogrulamak hicbir sey korumazdi - pickle zaten
yuklenirken calisirdi.

ARIZA YONU KAPALI: dogrulama gecmezse model YUKLENMEZ ve siniflandirma
uclari 503 doner. Servis ayakta kalir ama sessizce dogrulanmamis bir
modelle cevap URETMEZ.
"""
import hashlib
import os
import threading

from fastapi import FastAPI, HTTPException
from huggingface_hub import snapshot_download
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI(title="ALPHAWISE - FinBERT Sentiment Service")

MODEL_ADI = "ProsusAI/finbert"

# Sabitlenen surum. Bu, denetim aninda uretimde ZATEN calisan ve olculen
# (10 cumlelik sette 8/10) surumun ta kendisidir; HF'te 2023-05-23'ten beri
# degismemistir. Yani pin EKLEMEK davranisi DEGISTIRMEZ, yalnizca gelecekteki
# sessiz degisikligi keser.
REVISION = "4556d13015211d73dccd3fdd39d39232506f3e43"

# Uretimde calisan dosyalarin OLCULEN sha256 degerleri (sha256sum ile
# konteyner icinde hesaplandi, 01.09.2026). Buradaki her deger, o gun
# gercekten hizmet veren baytlarin parmak izidir.
BEKLENEN_SHA256 = {
    "pytorch_model.bin": "e15a7b5738df7f17553399b6d94c6e2ff69c89245d066e8e5d183f5803a554e3",
    "config.json": "f6449ddda85eb726207a40be59c0cd3bd4b142ccb27298d5e45f9ae3396b1abe",
    "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
    "tokenizer_config.json": "ffc7913f6084b138dad68de5a0c2f0ee25ac983709260901e01f53be5796b9d9",
    "special_tokens_map.json": "303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3",
}

# tf_model.h5 / flax_model.msgpack (her biri ~418 MB) BILINCLI olarak
# indirilmez: PyTorch yolu onlari kullanmaz, ama indirilirlerse hem 836 MB
# gereksiz yer kaplar hem de dogrulanmamis ek dosya yuzeyi olustururlar.
INDIRILECEK = tuple(BEKLENEN_SHA256)

# FAZLADAN AGIRLIK DOSYASI REDDI - OLCULEN ATLATMA (01.09.2026 supheci turu).
# "Adi gecen 5 dosyayi dogrulamak" YETMEZ, cunku transformers agirlik dosyasi
# secerken model.safetensors'i pytorch_model.bin'e TERCIH EDER. Snapshot
# klasorune dogrulanmamis bir model.safetensors birakildiginda:
#     - sha256 kapisi GECTI (cunku o dosya listede yok, bakilmiyordu)
#     - transformers O DOSYAYI yukledi
#     - duygu ciktisi TERSINE dondu (negative -> positive)
#     - /health hala "gecti: true" diyordu
# Yani kod "yukledigi seyi" degil, "adi sabit 5 dosyayi" dogruluyordu.
# Duzeltme: yuklemeden once klasorde BEKLENEN disinda HICBIR agirlik dosyasi
# bulunmadigi da dogrulanir. Ariza yonu kapali: taninmayan agirlik = RED.
AGIRLIK_UZANTILARI = (".safetensors", ".bin", ".h5", ".msgpack", ".ckpt",
                      ".pt", ".pth", ".onnx")

_classifier = None
_kilit = threading.Lock()
_dogrulama = {"calisti": False, "gecti": False}


def _sha256(yol: str) -> str:
    ozet = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1024 * 1024), b""):
            ozet.update(parca)
    return ozet.hexdigest()


def _dogrulanmis_model_yolu() -> str:
    """Sabitlenen surumu indirir, sha256 dogrular, yerel yolu dondurur.

    Dogrulama BASARISIZ olursa istisna firlatir ve model HIC yuklenmez -
    yani pickle deserialize EDILMEZ.
    """
    yol = snapshot_download(
        repo_id=MODEL_ADI,
        revision=REVISION,
        allow_patterns=list(INDIRILECEK),
    )
    uyusmayan = []
    for ad, beklenen in BEKLENEN_SHA256.items():
        tam = os.path.join(yol, ad)
        if not os.path.exists(tam):
            uyusmayan.append(f"{ad}: DOSYA YOK")
            continue
        gercek = _sha256(tam)
        if gercek != beklenen:
            uyusmayan.append(f"{ad}: beklenen {beklenen[:16]}... gelen {gercek[:16]}...")

    # Beklenen disinda AGIRLIK dosyasi var mi? (bkz. AGIRLIK_UZANTILARI notu)
    for kok, _dizinler, dosyalar in os.walk(yol):
        for ad in dosyalar:
            if ad in BEKLENEN_SHA256:
                continue
            if ad.lower().endswith(AGIRLIK_UZANTILARI):
                goreli = os.path.relpath(os.path.join(kok, ad), yol)
                uyusmayan.append(f"{goreli}: BEKLENMEYEN AGIRLIK DOSYASI (dogrulanmamis)")

    if uyusmayan:
        raise RuntimeError(
            "MODEL BUTUNLUK DOGRULAMASI BASARISIZ - model YUKLENMEDI "
            "(pickle deserialize EDILMEDI). Uyusmayan: " + "; ".join(uyusmayan)
        )
    return yol


def get_classifier():
    """Modeli bir kez, KILIT ALTINDA yukler.

    KILIT NEDEN SART - OLCULEN KUSUR (01.09.2026 supheci turu): FastAPI'nin
    `def` uclari bir is parcacigi havuzunda kosar ve korumasiz
    "if _classifier is None" bir kontrol-sonra-ata yarisidir. Olculdu: 8 es
    zamanli soguk istek -> _dogrulanmis_model_yolu() 8 KEZ, pipeline() 8 KEZ
    cagrildi; 8 kez 440 MB'lik sha256 hesaplandi ve 8 kopya BERT ayni anda
    bellege yuklendi (39 sn). Ariza-acik degil ama soguk baslangicta gercek
    bir bellek/DoS riski.
    """
    global _classifier
    if _classifier is not None:
        return _classifier
    with _kilit:
        if _classifier is None:                # kilit alindiktan sonra tekrar bak
            yol = _dogrulanmis_model_yolu()    # once dogrula...
            siniflandirici = pipeline("sentiment-analysis", model=yol)  # ...sonra yukle
            _dogrulama.pop("hata", None)       # basari: eski hata metnini BIRAKMA
            _dogrulama["calisti"] = True
            _dogrulama["gecti"] = True
            _classifier = siniflandirici
    return _classifier


def _siniflandirici_veya_503():
    """Dogrulama gecmeden siniflandirma YAPILMAZ (ariza yonu kapali)."""
    try:
        return get_classifier()
    except Exception as e:
        _dogrulama["calisti"] = True
        _dogrulama["gecti"] = False
        _dogrulama["hata"] = f"{type(e).__name__}: {e}"
        raise HTTPException(503, {
            "neden": "Model butunluk dogrulamasi gecilmedi; siniflandirma yapilmaz.",
            "dogrulama": _dogrulama,
        })


class SentimentRequest(BaseModel):
    text: str


class BatchSentimentRequest(BaseModel):
    texts: list[str]


@app.get("/health")
def health():
    # DURUM DOGRULAMAYI YANSITIR - OLCULEN KUSUR (01.09.2026 supheci turu):
    # status sabit "ok" idi; butunluk dogrulamasi COKMUSKEN bile /health 200
    # "ok" donuyor ve compose healthcheck'i (yalnizca HTTP 200'e bakar)
    # konteyneri "healthy" gosteriyordu - butun siniflandirma uclari 503
    # verirken. Artik dogrulama basarisizsa status bunu soyler.
    #
    # Dogrulama HIC calismamissa (soguk servis) durum "hazir_degil"dir:
    # "ok" demek, denenmemis bir seyi onaylamak olurdu.
    if not _dogrulama.get("calisti"):
        durum = "hazir_degil"
    elif _dogrulama.get("gecti"):
        durum = "ok"
    else:
        durum = "butunluk_dogrulamasi_basarisiz"
    return {
        "service": "FinBERT",
        "status": durum,
        "siniflandirabilir": bool(_dogrulama.get("gecti")),
        "model": MODEL_ADI,
        "revision": REVISION,
        "butunluk_dogrulamasi": _dogrulama,
        "not": ("Model surumu sabitlenmistir ve dosyalar sha256 ile, pickle "
                "yuklenmeden ONCE dogrulanir. Dogrulama gecmezse siniflandirma "
                "uclari 503 doner."),
    }


@app.post("/sentiment")
def analyze_sentiment(req: SentimentRequest):
    """Tek bir finansal metnin sentiment'ini analiz eder (positive/negative/neutral)."""
    classifier = _siniflandirici_veya_503()
    result = classifier(req.text)[0]
    return {
        "text": req.text,
        "label": result["label"],
        "score": round(result["score"], 4),
    }


@app.post("/sentiment/batch")
def analyze_sentiment_batch(req: BatchSentimentRequest):
    """Birden fazla metni tek seferde analiz eder (orn. SAA'nin haber basliklari)."""
    classifier = _siniflandirici_veya_503()
    results = classifier(req.texts)
    return {
        "results": [
            {"text": t, "label": r["label"], "score": round(r["score"], 4)}
            for t, r in zip(req.texts, results)
        ]
    }
