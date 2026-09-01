# FinBERT Sentiment Servisi

Finansal metin duygu analizi (positive / negative / neutral). GPU gerektirmez,
CPU'da calisir. SAA (Sentiment Analysis Agent) bu servisi `/sentiment/batch`
uzerinden cagirir; SAA'nin uretttigi `overall` alani MAA'nin karar skoruna girer.

| | |
|---|---|
| Model | `ProsusAI/finbert` (HuggingFace) |
| Sabitlenen surum | `4556d13015211d73dccd3fdd39d39232506f3e43` |
| Parametre | ~110M (bert-base) |
| Port | `127.0.0.1:8070` |
| Uclar | `GET /health`, `POST /sentiment`, `POST /sentiment/batch` |

## Tedarik zinciri sabitlemesi (01.09.2026)

Servis, model surumunu **sabitler** ve indirilen dosyalari **pickle
yuklenmeden ONCE** sha256 ile dogrular.

**Neden gerekliydi.** Onceki surum su tek satiri kullaniyordu:

```python
pipeline("sentiment-analysis", model="ProsusAI/finbert")
```

Ne revision pin'i ne butunluk dogrulamasi vardi. Model deposu HF tarafinda
(kazayla ya da kotu niyetle) degistirilse sistem yeni dosyayi **sessizce**
yuklerdi. Bu ozellikle onemli, cunku bu depoda yuklenen dosya **pickle**'dir:

```
resolve/main/model.safetensors  -> HTTP 404   (yok)
resolve/main/pytorch_model.bin  -> HTTP 200   (yuklenen bu)
```

Pickle deserializasyonu tanim geregi **kod calistirir**.

**`use_safetensors=True` neden cozum degil.** Bu depoda safetensors yalnizca
**birlestirilmemis ucuncu taraf PR dalinda** (`refs/pr/29`) bulunuyor. O bayrak
verildiginde `transformers` sessizce o dogrulanmamis dala duser — riski
azaltmaz, baska bir tedarik zinciri riskine cevirir. Denetimde olculdu ve bu
yol bilincli olarak reddedildi.

**Secilen cozum.** Revision pin + sha256 dogrulama. "Modeli kendi altyapimizda
barindirma" secenegi degerlendirildi ve secilmedi: ilk kopyayi yine HF'ten
alacagimiz icin tedarik zinciri riskini kaldirmiyor, buna karsilik kalici
depolama ve guncelleme sorumlulugu ekliyor.

**Sira kritik.** `snapshot_download()` dosyalari yalnizca *indirir* (deserialize
etmez); sha256 dogrulamasi ondan sonra, `from_pretrained` cagrilmadan once kosar.
Once yukleyip sonra dogrulamak hicbir sey korumazdi — pickle zaten yuklenirken
calisirdi.

**Ariza yonu kapali.** Dogrulama gecmezse model yuklenmez ve siniflandirma
uclari `503` doner. Servis ayakta kalir ama sessizce dogrulanmamis bir modelle
cevap uretmez. Durum `GET /health` -> `butunluk_dogrulamasi` alaninda gorunur.

`tf_model.h5` ve `flax_model.msgpack` (her biri ~418 MB) bilincli olarak
indirilmez: PyTorch yolu onlari kullanmaz, indirilirlerse hem gereksiz yer
kaplar hem de dogrulanmamis ek dosya yuzeyi olustururlar.

## ⚠️ LISANS BELIRSIZLIGI — ticari moda gecmeden once okunmali

**Kod ile agirliklarin lisans durumu FARKLIDIR ve bu ayrim kritiktir.**

| Artefakt | Kaynak | Lisans | Bizim kullandigimiz |
|---|---|---|---|
| Kaynak kodu | `github.com/ProsusAI/finBERT` | **Apache-2.0** (dogrulandi) | ❌ hayir |
| Model agirliklari | `huggingface.co/ProsusAI/finbert` | **BEYAN EDILMEMIS** | ✅ **evet** |

Olculen kanit (01.09.2026):

```
huggingface.co/api/models/ProsusAI/finbert
  cardData.license : YOK
  license etiketi  : YOK
  model kartinin ham metninde "license" kelimesi HIC gecmiyor
```

Yani **fiilen kullandigimiz artefaktin (agirliklar) lisansi beyan edilmemistir.**
Beyan edilmemis lisans, varsayilan olarak "tum haklari sakli" anlamina gelir.

### CONSTITUTION.md'de duzeltilmesi onerilen kayit

Anayasa satir 148 su an sunu diyor:

```
| FinBERT | github.com/ProsusAI/finbert | Apache-2.0 | Ingilizce ABD haber sentiment |
```

Bu kayit **teknik olarak dogru ama yaniltici**: Apache-2.0 olan sey GitHub
**kod** deposudur; biz o kodu degil, HuggingFace'teki **agirliklari**
kullaniyoruz ve onlarin lisansi beyan edilmemistir. Anayasa bu haliyle
sahip olmadigimiz bir guvence veriyor.

### Kullanim baglamina gore risk

- **Bugunku kullanim (God Mode, kisisel/deneme):** pratik risk dusuk. Model
  kamuya acik, gated degil, 5,02M indirme almis, akademik olarak yayimlanmis
  (arXiv:1908.10063). Dagitim yapmiyoruz.
- **Ticari moda gecis (Elite):** bu madde **cozulmesi gereken bir engeldir**.
  Beyan edilmemis lisans, ticari kullanim izni vermez.

### Oneri: ticari-moda-gecis hatirlatma listesine EKLENMELI

Anayasa'da OpenBB icin zaten boyle bir uyari var (satir 134: *"Ticari faza
gecisde ya izole container'a alinir ya da cikarilir"*). FinBERT ayni listeye
eklenmelidir, cunku sorunun turu ayni sinif: **kisisel kullanimda sorun
yaratmayan, ticari dagitimda engel olusturan lisans durumu.**

Ticari faza gecmeden once yapilmasi gerekenler:
1. ProsusAI'ye agirliklarin lisansi icin yazili olarak sorulmasi, veya
2. Acikca lisansli bir alternatife gecilmesi (or. Apache-2.0 / MIT beyanli bir
   finansal duygu modeli), veya
3. Kendi modelimizin acikca lisansli bir veri setiyle egitilmesi.

## Testler

Servisin 10 cumlelik referans test setindeki taban dogrulugu **8/10 (%80)**
(olculdu 01.09.2026). Iki hatasi da notr cumlelerde:

- `"Trading volume was in line with the 30-day average during the session."`
  -> positive (guven 0.4755 — model kendi kararsizligini ele veriyor)
- `"The index closed unchanged as gains in energy offset losses in technology."`
  -> negative (guven 0.8246)

Bu taban, surum sabitlemesi **oncesi ve sonrasi** ayni olmalidir; pin, o gun
uretimde zaten calisan surumu sabitledigi icin davranisi degistirmez.
