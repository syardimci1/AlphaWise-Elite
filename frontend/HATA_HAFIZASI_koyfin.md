# Hata Hafızası — Koyfin Olay Katmanı

Yalnızca ekleme, silme yok. Kural: aynı hata 2. kez → DUR-SOR. Aynı kök
neden farklı kılıkta 2. kez → DUR-SOR.

## [2026-09-15T00:00] H-001

**Belirti:** Bir önceki fizibilite incelemesinde (madde 59, önceki
oturum) "dark pool verisi haftalık özet, günlük ayrık olay değil, bu
yüzden marker'a uygun değil / veri modeli değişikliği gerekir" sonucuna
varılmıştı.

**Kök neden (5 Neden):**
1. Neden yanlış sonuca varıldı? → yalnızca `finra-darkpool-service`'in
   dashboard'da KULLANILAN ucu (`/darkpool/{ticker}`) incelenmişti.
2. Neden yalnızca o uç incelendi? → inceleme dashboard/page.tsx'in
   MEVCUT çağrılarından yola çıkmıştı, servisin TÜM uç listesi
   (`/openapi.json`) çekilmemişti.
3. Neden tüm uç listesi çekilmedi? → önceki görev "mevcut panelleri
   tespit et" diyordu, "servisin sahip olduğu TÜM uçları tara" demiyordu
   — kapsam dar yorumlandı.
4. Neden bu dar yorum bir hataya yol açtı? → aynı servis, kullanılmayan
   bir ucunda (`/regsho/{ticker}`) GÜNLÜK granülerlikte veri taşıyordu;
   dar kapsam bunu gözden kaçırdı.
5. Kök neden: **"Panel = tüm veri kaynağı" varsayımı yanlıştı.** Bir
   backend servisin frontend'de gösterilen ucu, o servisin sahip olduğu
   TEK uç olmak zorunda değildir.

**Düzeltme:** FAZ 1'de `curl .../openapi.json` ile 4 servisin TÜM
uçları listelendi (bkz. `contracts/kaynak_haritasi.md`). `/regsho/{ticker}`
bulundu: günlük FINRA Reg SHO kısa-hacim oranı, 10 günlük pencere,
ayrıştırma gerekmeden marker'a hazır. Dark pool artık "veri modeli
değişikliği gerekir" DEĞİL, "mevcut ama kullanılmayan bir uç zaten var"
kategorisine taşındı (commit: bu fazın contracts/ commit'i).

**Regresyon testi id:** yok — bu bir KOD hatası değil, bir ARAŞTIRMA
kapsam hatasıydı. Regresyon karşılığı: `kaynak_haritasi.md`'nin kendisi
artık 4 servisin `/openapi.json`'ı taranarak yazıldı, gelecekte tekrar
"tek panel = tek gerçek" varsayımına düşülmesini önlemek için bu dosya
her yeni kaynak eklendiğinde AYNI yöntemle (openapi tarama) güncellenmeli.

**Tekrar riski:** Orta — yeni bir veri kaynağı eklenirken yine yalnızca
"şu an gösterilen" uca bakılabilir. Azaltıcı: bu dosyanın kendisi,
gelecekteki bir incelemenin başında okunacak ilk belge.
