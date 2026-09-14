# KAPANIŞ — Madde 47: TUT/BEKLE Eşiği

## Başlangıç Bloğu

- `HATA_HAFIZASI_madde47.md`: yok (ilk çalışma)
- `VARSAYIM_DEFTERI_madde47.md`: yok (ilk çalışma)
- `KAPANIS_madde47.md`: yok (bu dosya)
- HEAD (AlphaWise-Elite): `7b0eadacbb243c81fc6c5632866dfcf44e95436e`
- Branch: `main`
- Zaman: `2026-09-13T01:20:06Z`

## Bölüm 0.1 — Çakışma Kontrolü

`git status --porcelain -- maa/src/main.py maa/src/isabet.py maa/src/isabet_olcut.py taa/src/main.py`
→ **boş** (bu dört dosyada başka bir oturumun commit'lenmemiş değişikliği yok).
`godmode-paper-trading-service/src/main.py` de temiz.
(Kirli dosyalar var ama farklı dosyalarda: `maa/src/cascade.py`,
`maa/src/llmquant_client.py` — başka bir görevden kalma, bu göreve dokunmuyor.)

## Bölüm 0.2 — İki Bulgunun Kimliği

### Kanıt

```
$ git log --oneline -n 30 -- maa/src/main.py maa/src/isabet.py
955e5e8 feat(olcum): karar isabeti - sansla ayirt edilemeyen oran raporlanmiyor
b1015ee fix(maa): SCORE_MEANINGS metin duzeltmesi
...

$ git log --oneline -- maa/src/isabet_olcut.py
b347a93 fix(isabet): TUT olcutu duzeltildi + KENDI TABAN OLCUMUMDEKI HATA giderildi
e37a7be fix(isabet): TUT olcutu piyasaya goreli oldu, BEKLE puanlanmiyor
(dosya e37a7be'de OLUŞTURULDU)

$ git log -S '0.05' --oneline -- maa/src/main.py maa/src/isabet.py maa/src/isabet_olcut.py
b347a93 fix(isabet): TUT olcutu duzeltildi + KENDI TABAN OLCUMUMDEKI HATA giderildi
90d15fb feat(maa): restructure MAA into dedicated folder

$ grep -n "0\.15" maa/src/main.py
921:                was_correct = abs(pct_change) < 0.15

$ grep -n "0\.05" maa/src/isabet_olcut.py
88:TUT_GORELI_ESIK = 0.05
```

### Zaman çizelgesi (aynı gün, 3 commit)

| Saat | Commit | Ne yaptı |
|---|---|---|
| 15:55 | `955e5e8` | `isabet.py`'yi **oluşturdu**: mutlak ±%15 ölçütünü eleştirdi, "taban %71,9" bulgusunu raporladı |
| 22:03 | `e37a7be` | `isabet_olcut.py`'yi **oluşturdu**: piyasaya göreli ±%10 ölçütü önerdi (bu, "sabahki düzeltme" olarak anılan ilk sürüm) |
| 23:17 | `b347a93` | `isabet_olcut.py`'yi **düzeltti**: ±%10'daki kendi taban ölçümü hatalıydı (yanlış evren + tamamen örtüşen pencereler), yeniden ölçüp **±%5**'e (taban %47,7) geçti |

### Karar (Bölüm 0.2 karar ağacına göre)

**Aynı değişkeni işaret ediyorlar** — `isabet.py`'nin eleştirdiği "TUT dogru <= |getiri|<%15" ölçütü ile `isabet_olcut.py`'nin çözdüğü sorun **aynı ölçüt**. Ama `isabet.py` **kod değil, dondurulmuş bir bulgu belgesi**dir: 955e5e8'de yazıldıktan sonra hiç güncellenmemiş, hâlâ eski "taban %71,9" rakamını taşıyor. `isabet_olcut.py` ise canlı, test'le doğrulanan, gerçek ölçüt modülüdür (`TUT_GORELI_ESIK = 0.05`, `TUT_GORELI_TABAN = 0.477`, `test_isabet_taban.py` ile veriden yeniden hesaplanıp kilitleniyor).

**Sonuç: tutarsızlık gerçek ama önceden zaten kapatılmış** — düzeltme `isabet.py`'ye değil, `isabet_olcut.py`'ye (doğru yere) yansımış; `isabet.py` ise güncellenmeden, yanıltıcı bir belge olarak kalmış. **Asıl iş: `isabet.py`'nin eskimiş bulgusunu düzeltmek/işaretlemek.**

## 🛑 KRİTİK BULGU — Görevin Y2'si proje kuralıyla çelişiyor

Görev metninin Y2 maddesi *"`maa/src/main.py` ve `isabet.py`'ye dokunma izni var"* diyor.
Ancak bu depodaki **CLAUDE.md** (proje kuralı, sistem talimatlarına göre
*"her şeyin üzerinde"* ve harfiyen uyulması gereken bir belge) şunu söylüyor:

> **KORUNAN DOSYALAR** — Aşağıdaki dosyalara TEK SATIR bile dokunulamaz:
> `maa/src/cascade.py`, **`maa/src/main.py`**, `maa/src/llmquant_client.py`

Ayrıca kalıcı bir kullanıcı hatırası (`korunan_dosyalar.md`) bu listenin
CLAUDE.md'dekinden de **geniş** olduğunu, `taa/src/main.py`'yi de kapsadığını
belirtiyor.

**Karar: CLAUDE.md üstündür. `maa/src/main.py`'ye bu görevde de TEK SATIR
dokunulmayacak** — görev metninin aksi yöndeki iznine rağmen. Bu, görevin
kendi Y1'iyle (taa/src/main.py, godmode main.py) tutarlı bir genişletmedir,
çelişki değildir; yalnızca Y2'nin main.py kısmı geçersiz sayılır.

**Bunun pratik sonucu:** `isabet_olcut.py` zaten bu ilkeye göre tasarlanmış
(kendi docstring'i, 10.09.2026): *"BU MODÜL KORUNAN main.py'YE DOKUNMAZ...
main.py içindeki evaluate_decisions() ve yazdığı was_correct alanı OLDUĞU
GİBİ KALIR. Bu modül ONUN YANINA ikinci bir değerlendirme kurar."*
Yani bu görevin kapsamı zaten `main.py`'ye dokunmadan yürütülebilir bir
mimariye oturuyor — Model Yükseltme Noktası 2 (main.py'ye dokunmadan izole
çözüm yoksa) **tetiklenmiyor**, çünkü izole çözüm zaten mevcut desende var.


---

## Ön-Kayıt Uyum Raporu

Sapma yok. `ON_KAYIT_madde47.md` (commit `5b44eea`) ölçümden önce yazıldı,
ölçüm sırasında değiştirilmedi. A için yalnızca ±%5 test edildi (yeniden
tarama yok); B için önceden sabitlenen {±%3,±%5,±%7} test edildi, hepsi
FDR'ye tabi tutuldu.

## Bağımsızlık Kontrolü Sonucu

Örtüşme **doğrulandı**: mevcut `_taban()` günlük kaydırılan 30 günlük
pencereler kullanıyordu (29 gün ortak bitişik pencereler arasında).
**Seçilen yöntem: (b) örtüşmeyen pencereleme** (blok bootstrap değil —
gerekçe `ON_KAYIT_madde47.md`'de). Sonuç: A için n **11.373 (ham) → 382
(n_eff)**. B zaten küçük/kümelenmiş gerçek veri (n=12, n_eff≤4 benzersiz
gün).

## 3 Seçeneğin Ölçüm Tablosu

| Seçenek | Taban (p̂) | n (n_eff) | Wilson %95 GA | Cohen's h | FDR-sonrası p | Yeterli güç mü |
|---|---|---|---|---|---|---|
| **A** (±%5, canlıda zaten uygulanmış — 10.09.2026) | 0,5105 | 382 | [0,4605; 0,5602] | +0,0209 | anlamlı değil | Evet (n_eff=382 ≥ n_min gerekli değerlerin çoğunda) |
| **B** (BEKLE, δ=%3) | 0,1667 | 12 (n_eff≤4) | [0,047; 0,448] | −0,730 | **anlamlı değil** (FDR düzeltmesiyle) | **Hayır** (n_min=10 ham bazda bile zar zor, n_eff=4'te kesinlikle hayır) |
| **B** (BEKLE, δ=%5) | 0,4167 | 12 (n_eff≤4) | [0,193; 0,680] | −0,167 | anlamlı değil | Hayır (n_min=275) |
| **B** (BEKLE, δ=%7) | 0,5833 | 12 (n_eff≤4) | [0,320; 0,807] | +0,167 | anlamlı değil | Hayır (n_min=275) |
| **C** (dokunmama) | — | — | — | — | — | bkz. aşağıdaki nicel özet |

**C'nin nicel özeti:** A zaten uygulanmış ve n_eff-düzeltmesiyle **doğrulandı**
(değişiklik gerekmiyor — "dokunmama" zaten fiili durum). B için "dokunmama"
= BEKLE `uygulanamaz` (puanlanmayan) kalmaya devam eder — bu, canlı
sistemde **zaten** gerçekleşen durumdur (`goreli_sonuc='uygulanamaz'`,
12 kayıtta doğrulandı) ve commit `232d1a0`'ın ilkesiyle (ölçülemedi ≠ sıfır)
**tutarlıdır**. B'yi puanlı bir ölçüte çevirmenin maliyeti — mevcut kanıtla
— yanlış-güvenli bir sonuç üretme riskidir (n=12'nin 8'i tek günde, tesadüfi
piyasa hareketini "BEKLE doğruydu/yanlıştı" diye yorumlama riski).

## Şüphecilik Turu

`VARSAYIM_DEFTERI_madde47.md` V-005…V-010'da tam metin. Özet: cherry-picking
yok (ön-kayıt+FDR), bağımsızlık düzeltildi, holdout'a bakılmadı, veri sürümü
sapmadı, örnek yeterliliği A'da var B'de yok, Simpson paradoksu yok ama
ciddi sembol-bazında heterojenlik var (açık soru), seçim yanlılığı yok.

## Model Yükseltme Noktası 1 — tetiklendi, onaylandı, çözüldü

**Tetiklenme (Sonnet+High):** BH-FDR sonrası hiçbir seçenek anlamlı değildi
ve B'nin örneklemi güç gereksinimini karşılamıyordu. Faz 2.2 gereği durup
Opus+High önerildi. **Kullanıcı onayladı** ve Opus+High ile devam edildi.

**Opus turunda çözülen asıl mesele:** Sonnet turunda "H_A yanlış
çerçevelenmiş olabilir" diye işaretlenen şüphe, burada **kanıta bağlandı**
ve karara dönüştürüldü (V-013…V-017).

---

## KARAR: **C** — A korunsun, B uygulanmasın

### A (TUT bandı ±%5) — DEĞİŞİKLİK GEREKMİYOR, doğrulandı

Ön-kayıttaki H_A **yanlış çerçevelenmişti**. Bir taban oranı 0,50'ye
yakınken Bernoulli varyansı `p(1−p)` maksimumdur; yani ölçüt sapmayı en
yüksek güçle saptar. ±%5 eşiğinin **tasarım hedefi tabanın 0,50'ye yakın
olmasıydı** — ondan uzaklaşması değil. Dolayısıyla "%50'den anlamlı farklı
mı?" testinin reddedilememesi, kalibrasyonun **başarısıdır**.

Y7 gereği ön-kayıt değiştirilmedi. Ön-kayıtlı test sonucu olduğu gibi
raporlandı (p=0,682) **ve** doğru belirtilmiş test (TOST eşdeğerlik)
**post-hoc etiketiyle** ayrıca yürütüldü. Marj post-hoc seçilmedi:
±0,10, projenin kendi kodunda (`maa/src/test_isabet_taban.py:124`,
commit `b347a93`, **bu görevden önce**) taahhüt edilmiş marjdır.

| Küme | p̂ | n_eff | Wilson %95 GA | TOST p | Eşdeğerlik |
|---|---|---|---|---|---|
| Geliştirme | 0,5105 | 382 | [0,4605; 0,5602] | 1,77e-04 | **KURULDU** |
| Holdout | 0,4606 | 165 | [0,3863; 0,5367] | 5,60e-02 | **KURULAMADI** (sınırda) |

**Holdout dürüstçe:** eşdeğerlik %95 güvenle **doğrulanamadı** (p=0,056).
Ama bu bir *başarısızlık kanıtı değil*, *doğrulama gücü yetersizliğidir*:
nokta tahmini (0,4606) marjın rahatça içinde, ve ön-kayıtlı **ikincil**
test iki dönem arasında **fark bulmuyor** (Newcombe GA
[−0,0412; +0,1393], sıfırı kapsıyor; Cohen's h=+0,0998). Ön-kayıtlı
**birincil** test de her iki kümede **aynı** sonucu veriyor. Yani holdout
geliştirmeyle çelişmiyor — yalnızca daha küçük.

→ **Eşik kararlı ve yazı-turaya yakın. Değiştirmek için gerekçe yok.**

### B (BEKLE'ye puanlı ölçüt) — UYGULANMASIN, üç bağımsız gerekçe

**(1) İstatistiksel.** FDR sonrası hiçbir δ anlamlı değil. n_eff≤11;
δ=%5/%7 için n_min=277 bağımsız gözlem — mevcut hızda (0,32 benzersiz
gün/takvim günü) **~2,3 yıl**.

**(2) Ampirik — asıl kanıt.** BEKLE dönemleri koşulsuz tabandan
**ayırt edilemiyor** ve görünen yön **eşiğe göre işaret değiştiriyor**:

| δ | BEKLE | Koşulsuz | Fark GA | Sıfırı kapsıyor | Görünen yön |
|---|---|---|---|---|---|
| %3 | 0,167 | 0,227 | [−0,182; +0,222] | evet | daha çalkantılı |
| %5 | 0,417 | 0,370 | [−0,178; +0,312] | evet | daha sakin |
| %7 | 0,583 | 0,491 | [−0,173; +0,317] | evet | daha sakin |

İşaretin eşikle dönmesi **gürültünün imzasıdır**. Aynı veriden yalnızca
eşik seçerek zıt iki anlatı üretilebiliyor — `b347a93`'ün kendi dersinin
("aynı veriden zıt iki yargı") tekrarı.

**(3) Kavramsal.** BEKLE = "ölçemedik" (geçerli katman < 3). Fiyat
hareketiyle puanlamak, ölçülemedi'yi piyasa çağrısına çevirir — commit
`232d1a0`'ın kapattığı hata. Ayrıca **ters teşvik** yaratır: sakin
piyasada çekimserliği ödüllendirir, çalkantılıda cezalandırır — oysa
çekimserlik en çok çalkantıda değerlidir.

→ **BEKLE `uygulanamaz` kalmalı** (canlıda zaten öyle: 12 kayıtta
`goreli_sonuc='uygulanamaz'`).

### C (dokunmama) — SEÇİLEN

A için değişiklik gerekmiyor (doğrulandı), B için kanıt yok ve ilke karşı.
Tek gerçek kusur — `isabet.py`'nin eskimiş %71,9 bulgusu — A/B/C
kararından **bağımsız** olarak zaten düzeltildi (`6680dd3`).

---

## Faz 3 — Uygulama

**Uygulanacak kod değişikliği YOK** (karar C). Faz 3.0'ın geri dönüş
etiketi yine de atıldı: `pre-madde47-*`.

Bu görevde yapılan tek kod değişikliği (`6680dd3`, `isabet.py` docstring
düzeltmesi) A/B/C kararından bağımsızdır ve şu kanıtlarla kapatıldı:
docstring-soyulmuş **AST özeti önce/sonra birebir aynı**; 2 yeni test;
mutasyon sınandı (TUT_GORELI_TABAN değiştirilince yeni test yakaladı).

## Faz 4 — Son Denetim

| Kriter | Sonuç |
|---|---|
| (a) Korunan dosyalar boş diff | ✅ `5b44eea~1..HEAD` içinde `maa/src/main.py`, `taa/src/main.py`, `cascade.py`, `llmquant_client.py` **hiç geçmiyor** |
| (b) Tüm testler PASS | ✅ **157 passed** (4 dosya hariç: önceden var olan `httpx` eksikliği, bu görevden bağımsız) |
| (c) AST temiz | ✅ `isabet.py` saf hesaplama modülü — yazma/IO çağrısı yok |
| (d) Hukuki dil | ✅ yasaklı kalıp taraması temiz |

**Not (Y1/Y2 çatışması):** Görevin Y2'si `maa/src/main.py`'ye izin
veriyordu; CLAUDE.md'nin **KORUNAN DOSYALAR** kuralı vermiyor. CLAUDE.md
üstün tutuldu, dosyaya dokunulmadı. Bu, kararı **etkilemedi** — çünkü
seçilen karar (C) zaten kod değişikliği gerektirmiyor.

## Önce/Sonra Kanıtı

Yalnızca `isabet.py` düzeltmesi için (A/B/C kararı henüz uygulanmadı):
kod-only AST özeti önce/sonra **birebir aynı** (`6680dd3` commit mesajı).

## Holdout Sonucu

**Tek seferlik açıldı** (Opus turunda, karar gerekçesini
doğrulamak için). Sonuç yukarıda V-014/V-015'te: nokta tahmini
geliştirmeyle uyumlu (0,4606 vs 0,5105), iki dönem arasında anlamlı fark
yok, ama eşdeğerlik %95 güvenle **doğrulanamadı** (TOST p=0,056, sınırda,
n_eff=165 nedeniyle). Ön-kayıtlı **birincil** test her iki kümede aynı
sonucu verdiği için "karar geri alınır" koşulu **tetiklenmedi** — ayrıca
geri alınacak bir karar da yok (C = değişiklik yok).

## Push Durumu

4 commit, **push kullanıcı onayı bekliyor**:
- `5b44eea` — ön-kayıt (pre-registration)
- `6680dd3` — `isabet.py` eskimiş bulgu düzeltmesi + 2 test
- `8cc733d` — Faz 0–2 belgeleri (Sonnet turu)
- (bu commit) — Faz 2 kararı + Faz 3–4 (Opus turu)

Rollback etiketi: `pre-madde47-*` (`6680dd3`'ten önce).
Geri alma: `git revert 6680dd3` (tek kod commit'i; diğerleri yalnızca belge).

## Kendi Bulduğum Hatalar

`HATA_HAFIZASI_madde47.md` Hata #1: `decision_log`'da tam yinelenen bir
BEKLE satırı (NVDA, 2026-08-02). Kök nedeni bu görevin kapsamı dışında.

## Açık Sorular (→ VARSAYIM_DEFTERI'ne [AÇIK SORU] olarak eklendi)

Bkz. aşağıdaki yeni V-011.

## Önerilen Sonraki 3 Adım (her biri ölçülebilir + geri alınabilir)

1. **BEKLE birikimini izle, ~2,3 yıl sonra B'yi yeniden aç.** Ölçülebilir:
   `decision_log`'da `decision='BEKLE' AND evaluated_at IS NOT NULL`
   benzersiz gün sayısı ≥ 277 olduğunda. Geri alınabilir: yalnızca gözlem.
2. **Holdout eşdeğerliğini yeniden ölç** (veri büyüdükçe). Bugün TOST
   p=0,056 ile sınırda kaldı; n_eff ~250'ye çıktığında kesinleşir.
   Ölçülebilir, geri alınabilir: yalnızca ölçüm.
3. **Sembol-bazında heterojenliği ele al** (V-011): sabit ±%5 bandının
   tabanı JEPI'de 0,914, NVDA'da 0,211. Volatiliteye normalize bir bant
   (ATR/β ayarlı) araştırılabilir — **ayrı bir madde**, bu görevin kapsamı
   dışında.

SONRA DUR — yeni iş icat etme.
