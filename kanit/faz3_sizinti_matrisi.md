# FAZ 3 — SIZINTI MATRİSİ (C4)

**Tarih:** 17 Eylül 2026 · **Kapsam:** A (kenar-öncelikli)
**Çalıştırma:** `cd frontend && npm test` · `db/testler/calistir.sh`

---

## 3.0 — Senaryolar ELLE yazılmadı, ÜRETİLDİ

`frontend/tests/kiracilik/sizinti-matrisi.test.ts`, `src/app/api` ağacını
gezip her `route.ts` için somut bir URL üretiyor ve **her rota için** A→B
erişim denemesi kuruyor. Böylece "hangi ucu unuttum?" sorusu insana kalmıyor:
yeni bir rota eklendiği an matrise giriyor.

Ölçülen kapsam:

```
[matris kapsami] 23 rota: {"PIYASA":19,"SISTEM":1,"KULLANICI":3}
```

| sınıf | adet | anlamı |
|---|---|---|
| `PIYASA` | 19 | kullanıcıdan bağımsız veri; **paylaşım TASARIMDIR**, sızıntı değil |
| `KULLANICI` | 3 | yanıtı kullanıcıya göre değişmesi gereken uçlar (`raporlar` ×2, `portfoy`) |
| `SISTEM` | 1 | bayrak/sağlık |

Bu sınıflandırma açıkça yazıldı ki matris "hepsi izole" gibi **yanlış bir
iddia** kurmasın. Kapsam A'da defter tek sistem hesabıdır; DPKE, 13F, kongre
ve makro uçlarının aynı yanıtı vermesi doğru davranıştır.

---

## 3.1 / 3.2 — Sonuçlar (gerçek oturumla, superuser DEĞİL)

Testler `middleware`'i **gerçek oturum çerezleriyle** sürüyor; kimlik
doğrulaması yerel bir saplama GoTrue'ya gidiyor. Hiçbir yerde "kimliği
varsayalım" kısayolu yok.

| # | iddia | kapsam | sonuç |
|---|---|---|---|
| 1 | Her rotada A kendi kimliğini, B kendi kimliğini taşır | 23/23 rota | ✅ |
| 2 | Hiçbir rotada A, B'nin kimliğini taşımaz | 23/23 rota | ✅ |
| 3 | Uydurma kimlik başlığı ezilir (taklit koruması) | 23/23 rota | ✅ |
| 4 | Bir kullanıcı kovasını tüketse bile diğeri geçer | 3 hız sınıfı (ucuz/sinyal/pahalı) | ✅ |
| 5 | Kimliksiz istek 401 alır ve kimlik taşımaz | 23/23 rota | ✅ |

### Veritabanı tarafı (izole ortam, gerçek `anon`/`authenticated`)

| test ağı | sonuç |
|---|---|
| `sizinti_testi.py` (satır düzeyi matris) | **30/30** |
| `yollar_testi.py` (JOIN/sequence/şema/katalog) | **13/13** |
| `goc_testi.py` (idempotentlik, veri korunumu, canlı yol) | **18/18** |
| `geri_alma_testi.py` (gidiş-dönüş) | **8/8** |
| `goruntuleme_kaydi_testi.py` (007 izolasyonu) | **14/14** |
| `bypass_testi.py` | **0 bulgu** |

Frontend: **187/187** (106 `.mjs` + 81 `.ts`).

---

## 3.3 — Meşru kullanım bozulmadı

19 piyasa ucunun her biri iki ayrı kullanıcıyla çağrıldı; **kullanıcı
kovasından ya da başka bir nedenden kaynaklanan tek bir kırılma yok**.

---

## ⚠ BULGU — ÖN KOVA HÂLÂ PAYLAŞIMLI (adalet mutlak değil)

İ-3 kullanıcı bazlı kovayı getirdi, ama hız sınırlaması **iki aşamalı**:

- **Aşama 1 (ön kova)** — anahtarı `on:${istemciKimligi(req)}|${sinif}` ve
  `istemciKimligi()` güvenilir vekil yokken **herkes için `'ortak'`** döndürüyor.
  İşi kredi paylaştırmak değil, Supabase doğrulama çağrısını selden korumak;
  tavanı sınıf tavanının **4 katı**.
- **Aşama 2 (kullanıcı kovası)** — anahtarı doğrulanmış kullanıcı kimliği,
  taklit edilemez, tavanı bugünkü ölçülmüş değerler.

**Ölçülen sınır** (`/api/raporlar`, `ucuz` sınıfı, patlama 30):

```
[on kova siniri] kendi kovasi 31. istekte, on kova 89. istekte doldu;
                 ikinci kullanici etkilendi: true
```

Yani: bir kullanıcı önce **kendi** kovasından düşüyor (doğru davranış), ama
yeterince yüklenmeye devam ederse ön kovayı da tüketip **diğer kullanıcıyı da**
429'a düşürebiliyor.

**Bu gizlenmiyor, ölçülüyor ve belgeleniyor.** Bilinçli bir ödünleşme:
- Ön kovayı kullanıcı bazlı yapmak, doğrulama sırasını tersine çevirmeyi
  (her istekte Supabase'e ağ çağrısı) gerektirirdi — dosyanın kendi
  "ucuz-önce/pahalı-sonra" ilkesine aykırı.
- Çerez değerinden türetilen ucuz bir ön kova ise taklit edilebilir olurdu ve
  bugünkünden **daha zayıf** olurdu.

**Kalan risk:** kötü niyetli ya da hatalı bir istemci, kendi kovasının ~3–4
katını aşarak diğerlerini geçici olarak kilitleyebilir. Bunun kalıcı çözümü
sistemin önüne **güvenilir bir ters vekil** koymaktır (`GUVENILIR_VEKIL=1`
o zaman anlamlı hâle gelir). Bu, bu görevin kapsamı dışındadır ve risk
defterine eklenmiştir.

---

## Test sırası bağımsızlığı (yöntem notu)

Matrisin ilk sürümü sondaki olumlu denetimde kırmızı veriyordu. Kök neden
**gerçek bir kırılma değil, test sırası artefaktıydı**: kovalar modül düzeyi
durum ve matrisin her testi 23 rotaya vuruyor, dolayısıyla sondaki test
tükenmiş bir kovayla karşılaşıyordu.

Tek tek yamamak yerine dosya **sıradan bağımsız** hâle getirildi: her test
kendi kullanıcı çiftini açıyor (`taseKullanicilar()`). Böylece yeni bir test
eklemek eskisini bozmuyor.

Ön kova ise paylaşımlı olduğu için hâlâ dosya boyunca birikiyor — bu yüzden
ön kova testindeki iddia bir **orana** değil **sıraya** bağlandı: "önce kendi
kovası, sonra ön kova". Orana bağlamak, testi diğer testlerin sayısına
bağımlı kılar ve her yeni testte kırardı.
