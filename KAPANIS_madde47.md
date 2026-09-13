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

## 🔴 MODEL YÜKSELTME ÖNERİSİ: Nokta 1

FDR sonrası **hiçbir seçenek anlamlı değil** (A: p=0,682; B'nin 3 eşiği de
FDR sonrası anlamsız) ve B'nin örnek büyüklüğü (n_eff≤4) hiçbir eşikte güç
gereksinimini karşılamıyor. Bu, istatistiksel belirsizlik altında karar
önerisi üretmek için daha güçlü akıl yürütme gerektiriyor. **Opus + High'a
geçilmesini öneririm. Onay verene kadar ilerlemeyeceğim.**

### Kullanıcıya sunulan 3 seçenek (ölçülmüş haliyle)

**A — TUT bandı ±%5 (zaten uygulanmış, 10.09.2026):**
n_eff-düzeltmesi seçimi **doğruladı** (eski %47,7 yeni %95 GA'nın içinde).
Literal olarak "%50'den anlamlı farklı" değil — ama bu muhtemelen **tasarım
hedefinin başarısı**: eşik bilerek yazı-tura noktasına kalibre edilmişti.
**Önerilen aksiyon: değişiklik gerekmiyor, mevcut durum korunsun.**
Risk: düşük (zaten canlıda, geri alma zaten mümkün — `git revert b347a93`).

**B — BEKLE için puanlı ölçüt tanımlamak:**
Gerçek veri (n=12, n_eff≤4) hiçbir δ için yeterli güce sahip değil.
Ayrıca commit `232d1a0`'ın "ölçülemedi ≠ sıfır" ilkesiyle **kavramsal
gerilim** taşıyor — BEKLE'yi fiyat hareketiyle puanlamak, tam olarak o
commit'in düzelttiği hatayı geri getirebilir.
**Önerilen aksiyon: BEKLE puanlanmasın, mevcut `uygulanamaz` durumu
korunsun** (zaten canlıda böyle). Risk: düşük (dokunmama).

**C — Dokunmama:**
A zaten yapılmış ve doğrulanmış durumda; B'nin puansız kalması hem veri
yetersizliği hem ilke tutarlılığı açısından **haklı**. `isabet.py`'nin
eskimiş bulgusu bu görevde ayrıca (A/B/C kararından bağımsız olarak)
düzeltildi (`6680dd3`).

**Önerim:** **C** (A zaten tamam, B'ye dokunulmasın), çünkü kanıt B'yi
desteklemiyor ve B, projenin kendi "ölçülemedi ≠ sıfır" ilkesiyle çelişebilir.
Ama bu benim önerim — karar sizde.

**BEKLİYORUM — kullanıcı onayı olmadan ilerlemeyeceğim.**

## Önce/Sonra Kanıtı

Yalnızca `isabet.py` düzeltmesi için (A/B/C kararı henüz uygulanmadı):
kod-only AST özeti önce/sonra **birebir aynı** (`6680dd3` commit mesajı).

## Holdout Sonucu

**Bakılmadı** (Faz 3'e geçilmediği için henüz gerekmiyor; A/B/C kararı
netleşirse ve bir kod değişikliği gerekirse o zaman çalıştırılacak).

## Push Durumu

3 commit, henüz push edilmedi (kullanıcı onayı bekleniyor, ayrıca Model
Yükseltme Noktası tetiklendiği için A/B/C kararı da bekliyor):
- `5b44eea` — ön-kayıt
- `6680dd3` — isabet.py düzeltmesi (bağımsız, A/B/C kararından etkilenmiyor)
- Rollback etiketi: `pre-madde47-<tarih>` (Faz 3.0, `6680dd3`'ten önce atıldı)

## Kendi Bulduğum Hatalar

`HATA_HAFIZASI_madde47.md` Hata #1: `decision_log`'da tam yinelenen bir
BEKLE satırı (NVDA, 2026-08-02). Kök nedeni bu görevin kapsamı dışında.

## Açık Sorular (→ VARSAYIM_DEFTERI'ne [AÇIK SORU] olarak eklendi)

Bkz. aşağıdaki yeni V-011.

SONRA DUR (Model Yükseltme Noktası 1 nedeniyle) — yeni iş icat etme.
