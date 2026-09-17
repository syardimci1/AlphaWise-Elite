# FAZ 0 — Ön-Uçuş Kontrol Listesi

**Tarih:** 16 Eylül 2026
**Durum:** ⛔ **ÇIKIŞ KAPISI GEÇİLMEDİ** — Y0.4 çakışma kontrolü tetiklendi, DUR-SOR.

---

## 0.4 Çakışma Kontrolü — **BOŞ DEĞİL**

```
$ git status --porcelain | grep -E "(guard|maa|defter|decision_log|middleware|auth)"
 M maa/src/cascade.py
 M maa/src/llmquant_client.py
?? maa/src/cascade.py.bak_054817
?? maa/src/finra_darkpool_client.py
?? maa/src/test_model_secimi.py
```

Kural açık: *"Boş değilse → DUR-SOR. Otomatik temizlik yok."* Duruldu.

Diğer iki depo temiz: `godmode-paper-trading-service` 0 girdi,
`godmode/execution` 0 girdi. Çakışma yalnızca `AlphaWise-Elite/maa/src/`
içinde.

### Bu değişiklikler ne

| dosya | ne yapıyor | tarih |
|---|---|---|
| `maa/src/cascade.py` (+21/−5) | `model_registry` ile dinamik model seçimi; `run_cascade`'e `paket` parametresi eklenmiş | 18.08.2026 |
| `maa/src/llmquant_client.py` (+20) | yeni `get_specific_institution_position()` fonksiyonu | 19.08.2026 |
| `maa/src/cascade.py.bak_054817` | yedek dosya | 18.08.2026 |
| `maa/src/finra_darkpool_client.py` | izlenmeyen yeni modül | – |
| `maa/src/test_model_secimi.py` | izlenmeyen test (197 satır) | – |

### ÖNEMLİ YAN BULGU — üretim, commit edilmemiş kod çalıştırıyor

Ölçüldü (konteyner içi dosya hash'i ile karşılaştırma):

| dosya | konteyner | çalışma ağacı | HEAD | sonuç |
|---|---|---|---|---|
| `cascade.py` | `1d0c151ef7c1a7dc` | `1d0c151ef7c1a7dc` | `1bfe63797f33e8a0` | konteyner **AĞACI** kullanıyor |
| `llmquant_client.py` | `29ce43b29bed4e19` | `29ce43b29bed4e19` | `86b453f53fe0da4d` | konteyner **AĞACI** kullanıyor |
| `main.py` | `6e9f429d4e947131` | `6e9f429d4e947131` | `6e9f429d4e947131` | üçü de **AYNI** ✅ |

`finra_darkpool_client.py` ve `model_registry.py` konteynerde **VAR**.

Yani bunlar "yarım kalmış kirli ağaç" değil, **dağıtılmış ama hiç commit
edilmemiş çalışan kod**. Konteyner temiz bir checkout'tan yeniden
kurulursa MAA sessizce dinamik model seçimini ve FINRA darkpool
istemcisini kaybeder. Bu, bu görevden bağımsız gerçek bir risktir.

Ayrıca `cascade.py` ve `llmquant_client.py` CLAUDE.md'nin **korunan
dosyaları** — yani hâlihazırda değiştirilmiş durumdalar. Bu tespit
raporlanıyor; **düzeltilmiyor** (başkasının işi, Y0.4 ve proje kuralı).

---

## 0.5 Ön-Uçuş Kontrol Listesi

| # | kontrol | durum |
|---|---|---|
| □ | Git çalışma alanı temiz mi? | ❌ **HAYIR** — 54 girdi, 5'i çakışma desenine uyuyor |
| □ | İzole ortam (branch `feature/coklu-kullanici-izolasyon`) hazır mı? | ❌ henüz açılmadı (kirli ağaç kararı beklendiği için) |
| □ | Korunan dosyaların SHA-256 + AST hash'i alındı mı? | ✅ **EVET** — `kanit/faz0_korunan_hashler.json` |

### Alınan hash'ler (C8 çapası)

| kural | dosya | satır | SHA-256 | AST (kod-only) |
|---|---|---|---|---|
| Y1 | `taa/src/main.py` | 296 | `accc62c256f7…` | `3b6d6b0cd793…` |
| Y1 | `maa/src/main.py` | 1149 | `6e9f429d4e94…` | `9035bada0ca7…` |
| Y1 | `godmode-paper-trading-service/src/main.py` | 1811 | `62fd16df1be0…` | `dbd47e6f4946…` |
| CLAUDE.md | `maa/src/cascade.py` | 257 | `1d0c151ef7c1…` | `b658764e22c5…` |
| CLAUDE.md | `maa/src/llmquant_client.py` | 153 | `29ce43b29bed…` | `4a7e53670be1…` |

**AST hash neden:** SHA-256 yorum/boşluk değişikliğinde de döner. AST
hash docstring'leri soyup yalnızca çalıştırılabilir yapıyı hash'ler —
"kod değişmedi" iddiasını yorum düzenlemelerinden bağımsız kanıtlar.

`maa/src/main.py`'nin konteyner/ağaç/HEAD hash'i **aynı** — yani Y1
çapam temiz bir zeminde duruyor, çakışma onu etkilemiyor.

---

## Şüphecilik Turu (Y3)

**"Yanlış branch'te miyim?"** — Evet, `main`'deyim; görev
`feature/coklu-kullanici-izolasyon` istiyor. Branch açılmadı çünkü kirli
ağaçtan branch açmak o beş dosyayı benim çalışma alanıma taşır ve her
`git status` tabanlı kanıtımı kirletir. Önce karar gerekiyor.

**"Hash'ler doğru mu?"** — İki bağımsız yöntemle alındı (bayt SHA-256 +
docstring'siz AST) ve konteynerdeki kopyalarla karşılaştırıldı. `main.py`
üçlüsü tutarlı.

**"Bu çakışma gerçekten benim işimi etkiliyor mu, yoksa grep deseni mi
geniş?"** — Desen geniş: `maa` alt dizesi her yolu yakalıyor. Planlanan
mimaride (C2/Y8) `maa/src/` altına **hiç dokunulmuyor**. Ama iki gerçek
temas noktası var: (1) Y4.5 "`karar_uret` aynı girdi→aynı çıktı"
regresyonunun taban çizgisi, üretimde gerçekten çalışan **ağaç**
sürümünden alınmalı, HEAD'den değil — aksi halde taban yanlış olur;
(2) her `git status` tabanlı kanıtta bu 5 girdiyi açıkça dışlamam
gerekir, yoksa "yalnızca benim dosyalarım" iddiası ölçülemez.

**"Kendi hash betiğim doğru mu?"** — AST hash'in gerçekten docstring'e
duyarsız, koda duyarlı olduğu FAZ 2'de mutasyon testiyle sınanacak;
şimdilik doğrulanmamış bir araçtır ve öyle işaretlenmiştir.

---

## KARAR (kullanıcı, 16.09.2026): **"Dokunma, yanında çalış"**

Seçenek A onaylandı. Uygulanan çapa mekanizması:

| dosya | işi |
|---|---|
| `kanit/faz0_baskasinin_isi_taban.txt` | Faz 0 anındaki 54 girdilik `git status` anlık görüntüsü — bundan sonra çıkan her girdi **benimdir** |
| `kanit/faz0_cakisan_dosya_hashleri.txt` | Çakışan 5 dosyanın SHA-256'sı — "dokunmadım" iddiası dosyanın listede görünmesiyle değil, **içeriğiyle** kanıtlanır |
| `kanit/faz0_korunan_hashler.json` | 5 korunan dosyanın SHA-256 + AST hash'i |
| `kanit/benim_dosyalarim.sh` | Üçünü birden ölçen betik; her fazda çalıştırılır |

Branch açıldı: `feature/coklu-kullanici-izolasyon`.

### Yakalanan ölçüm hatası (kendi hatam)

Taban çizgisini `kanit/` dizinini yarattıktan **sonra** aldım; dolayısıyla
`?? kanit/` "başkasının işi" listesine girdi ve ölçüm kendi dosyalarımı
göremez hâle geldi (55 girdi). Düzeltildi: taban çizgisinden `kanit/`
çıkarıldı (54 girdi) ve ölçüm artık `?? kanit/` çıktısını veriyor.

Bu, önceki görevde üç kez tekrarlanan hatanın aynısının dördüncüsüydü:
**kod doğruydu, ölçüt yanlıştı.** Bu yüzden aşağıdaki doğrulama yapıldı.

### AST hash aracı doğrulandı (mutasyon testi)

Şüphecilik turunda "kendi hash betiğim doğrulanmamış bir araçtır" diye
işaretlenmişti. Dört mutasyonla sınandı (`maa/src/main.py` üzerinde,
dosyaya yazmadan, bellekte):

| mutasyon | AST hash | beklenen | sonuç |
|---|---|---|---|
| M1 — yorum satırı eklendi | `9035bada0ca7286b` (aynı) | değişmemeli | ✅ (SHA değişti: `6e9f…`→`ca9c…`) |
| M2 — docstring tamamen değişti | `9035bada0ca7286b` (aynı) | değişmemeli | ✅ |
| M3 — `decision_log` INSERT'ündeki bir kolon adı değişti | `7d6aaf7c0f98bffb` | **değişmeli** | ✅ araç kör değil |
| M4 — boş satırlar eklendi | `9035bada0ca7286b` (aynı) | değişmemeli | ✅ |

M3 kritik olan: araç gerçek bir kod değişikliğini yakalıyor. Bu olmasaydı
"main.py'ye dokunmadım" kanıtı değersiz olurdu.

---

## ÇIKIŞ KAPISI: ✅ GEÇİLDİ

| # | kontrol | durum |
|---|---|---|
| □ | Git çalışma alanı temiz mi? | ⚠️ hayır — ama kullanıcı kararıyla **ölçülebilir şekilde ayrıştırıldı** (taban çizgisi + içerik hash'i) |
| □ | Branch `feature/coklu-kullanici-izolasyon` | ✅ açıldı |
| □ | Korunan dosya hash'leri | ✅ alındı **ve aracın kendisi doğrulandı** |

FAZ 1'e geçiliyor.
