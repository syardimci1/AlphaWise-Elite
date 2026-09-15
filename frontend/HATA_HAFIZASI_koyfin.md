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

## [2026-09-15T00:00] H-002

**Belirti:** FAZ 2'de `PriceChart.tsx`'i GERÇEK bir tarayıcıda (Playwright)
canlı test ederken candle verisi hiç yüklenmedi; konsolda
`"Access to fetch ... has been blocked by CORS policy"` ve
`TypeError: Failed to fetch` hatası.

**Kök neden (5 Neden):**
1. Neden fetch başarısız oldu? → tarayıcı, `market-data-service`'e
   (127.0.0.1:8160) DOĞRUDAN cross-origin istek attı ve o servis
   `Access-Control-Allow-Origin` başlığı döndürmüyor.
2. Neden doğrudan cross-origin istek atıldı? → `PriceChart.tsx`,
   `NEXT_PUBLIC_MARKET_DATA_URL` env değişkeniyle servis adresini
   TARAYICI paketine gömüyordu.
3. Neden bu desen kullanıldı? → bileşen `komponente aitti` (bkz.
   FAZ1_KANIT.md: hiçbir sayfaya bağlı değildi, muhtemelen erken/yarım
   bir taslak) — diğer 4 veri kaynağının hepsi zaten sunucu-tarafı
   `/api/*` proxy route'u (servisProxy) kullanıyordu, bu bileşen o
   kalıba HİÇ UYMAMIŞTI.
4. Neden bu daha önce fark edilmedi? → bileşen hiçbir sayfaya bağlı
   olmadığı için (madde 45, FAZ1 bulgusu) canlı tarayıcıda hiç
   ÇALIŞTIRILMAMIŞTI — yalnızca kod okunarak "çalışır görünüyor"
   varsayılmıştı.
5. Kök neden: **doğrulanmamış/bağlanmamış kod, "çalışıyor" sayılmıştı.**
   Ayrıca bu desen `frontend/src/lib/servis-proxy.ts`'in kendi
   belgelediği güvenlik ilkesini ("Servis adresi YALNIZCA sunucuda
   okunur, NEXT_PUBLIC_ KULLANILMAZ") doğrudan ihlal ediyordu.

**Düzeltme:** `src/app/api/market-data/[ticker]/route.ts` eklendi
(diğer 4 route'la BİREBİR aynı `servisProxy` kalıbı). `PriceChart.tsx`
artık `NEXT_PUBLIC_MARKET_DATA_URL`'i DEĞİL, `/api/market-data/{ticker}`'i
çağırıyor — hem CORS sorunu ortadan kalktı hem de servis adresi artık
yalnızca sunucuda, hem de middleware'in oturum/hız-sınırlama koruması
otomatik olarak bu veri kaynağına da uygulanmış oldu (önceden HİÇ
korumasızdı).

**Regresyon testi id:** ayrı bir birim testi YOK (bu route diğer 4
route'la aynı `servisProxy` yardımcısını kullanıyor, o zaten dolaylı
olarak üretimdeki diğer route'larla kanıtlanmış); canlı kanıt FAZ 2
kanıt dosyasında (Playwright ekran görüntüsü).

**Tekrar riski:** Düşük — artık TÜM veri kaynakları (5/5) aynı
`servisProxy` kalıbını kullanıyor, tutarlılık koddan okunabilir hale
geldi.
