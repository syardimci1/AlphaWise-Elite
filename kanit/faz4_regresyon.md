# FAZ 4 — REGRESYON AĞI

**Tarih:** 17 Eylül 2026 · **Kapsam:** A (kenar-öncelikli)
**Çalıştırma:** `cd frontend && npm test` · `./kanit/faz4_regresyon.sh`

Görev metninin 15 maddesinin **hepsi** ele alındı. Hiçbiri sessizce
atlanmadı; kapsam dışı kalan maddeler açıkça gerekçelendirildi.

---

## Sonuç tablosu

| # | madde | nerede | sonuç |
|---|---|---|---|
| 4.1 | Mevcut defter kaybolmadı | `faz4_regresyon.sh` | ✅ (aşağıya bakın) |
| 4.2 | Sızıntı matrisi tam PASS | `sizinti-matrisi.test.ts` | ✅ 8/8 |
| 4.3 | Admin/dar anahtar akışı çalışıyor | `faz4-regresyon.test.ts` | ✅ 2/2 |
| 4.4 | `main.py` AST hash sabit | `benim_dosyalarim.sh` | ✅ 8/8 dosya |
| 4.5 | `karar_uret` etkilenmedi | `faz4_regresyon.sh` | ✅ |
| 4.6 | Kimlik katmanı <50 ms | `faz4-regresyon.test.ts` | ✅ **12,73 ms** |
| 4.7 | 100 eşzamanlı kullanıcı, sızıntı yok | `faz4-regresyon.test.ts` | ✅ **100/100 doğru kimlik** |
| 4.8 | Hata senaryoları | `faz4-regresyon.test.ts` | ✅ 4/4 |
| 4.9 | Geri alma testi | `faz4_regresyon.sh` | ✅ 4/4 |
| 4.10 | Başka kullanıcının verisi loglanmıyor | `faz4-regresyon.test.ts` | ✅ 2/2 |
| 4.11 | Önbellek anahtarlarında kullanıcı | `faz4-regresyon.test.ts` | ✅ karar kilitlendi |
| 4.12 | Hata mesajları bilgi sızdırmıyor | `faz4-regresyon.test.ts` | ✅ 2/2 |
| 4.13 | Hız sınırlama kullanıcı başına | `faz4-regresyon.test.ts` | ✅ |
| 4.14 | Çıkış sonrası jeton geçersiz | `faz4-regresyon.test.ts` | ✅ |
| 4.15 | Aynı kullanıcı 2 cihazdan | `faz4-regresyon.test.ts` | ✅ 2/2 |

**Toplam: frontend 19/19 + konteyner 9/9 = 28/28.**
Ayrıca matris 8/8, izole db ağı 83/83, mevcut frontend testleri 187/187.

---

## Madde madde notlar

### 4.1 — Defter: iddia "kaybolmadı" değil, **"hiç dokunulmadı"**

Görev metni "mevcut 1244 karar + 8 işlem kayıpsız göç eder" diyordu; o cümle
defterin **bölüneceği** varsayımına dayanıyordu. Kapsam A defteri
bölmediği için doğru ve **daha güçlü** iddia şudur: bu görev defter şemasına
ya da onu yazan koda **hiç dokunmadı**.

Ölçüldü:
- Defter şemasında `user_id` **yok** (eklenmedi) ✅
- Bu görevin commit'lerinde `godmode-paper-trading` altında **hiçbir dosya
  değişmedi** ✅
- Canlı sayım bugün `1420/8/924` — 16 Eylül'de `1332/8/836`'ydı. **Artış
  normaldir**: cron hafta içi günde 4 kez yazıyor. Sayının sabit kalmasını
  beklemek yanlış olurdu; sabit kalması gereken şey **şema ve kod**dur.

### 4.5 — `karar_uret` etkilenmedi (statik ve kesin kanıt)

Görev taban çizgisinden (`origin/main`) bu yana değişen Python dosyası
**2 adet** ve **ikisi de `db/testler/` altında** (izole test koşucuları).
Karar yolunda tek satır değişmedi. Ek olarak 8 korunan dosyanın SHA-256 ve
docstring'siz AST hash'i sabit.

### 4.6 — Gecikme ölçümünün sınırı (dürüstçe)

Ölçülen **12,73 ms**, *yerel saplama* kimlik sunucusuyla. Gerçek Supabase'in
ağ gecikmesi buna **eklenir** — ama o, kimlik katmanının değil **altyapının**
maliyetidir ve zaten `oturumDogrula` bu görevden önce de çağrılıyordu.
Ölçülen şey: bu görevin eklediği işlem yükü.

### 4.7 — Yük testi: 100 eşzamanlı kullanıcı

100 farklı kullanıcı aynı anda istek attı; **100'ü de 200 aldı ve 100'ünün
de kimliği doğru taşındı**, sıfır karışma. Test `sinyal` sınıfında çalışıyor
(bkz. aşağıdaki yöntem notu).

### 4.11 — Önbellek: karar **kilitlendi**, değiştirilmedi

MAA proxy önbelleği ve işlem havuzu **bilerek global** kaldı. Gerekçe Faz 1'de
ölçüldü: MAA çıktısı ticker'ın fonksiyonudur, kullanıcı boyutu taşımaz —
dolayısıyla kullanıcı bazlı anahtarlamak **hiçbir sızıntı kapatmaz** ama
LLM kredisini kullanıcı sayısıyla **çarpar**.

Test bu kararı **kilitliyor**: biri "düzeltmek" için önbellek anahtarına
kullanıcı eklerse test kırmızıya döner ve karar yeniden tartışılır. Böylece
kredi sessizce çarpılamaz (CLAUDE.md Bütçe Onay Kuralı).

### 4.12 — Sebep ayrımı sızdırılmıyor

`401` yanıtlarının **gövdesi** "çerez yok" ile "geçersiz jeton" durumlarında
**birebir aynı**; ayrım yalnızca teşhis başlığında (`X-Oturum`). Saldırgan
gövdeden hangi aşamada takıldığını anlayamaz.

### 4.14 — "Çıkış" testinin dürüst sınırı

Jeton iptali Supabase'in işidir; bu görev ona dokunmadı. Test edilen şey
doğru olan şey: **kimlik sunucusu jetonu reddettiği anda erişim kesiliyor**
ve kimlik aşağı akışa geçmiyor. Yani middleware jetonu önbelleğe alıp eski
kararı sürdürmüyor.

---

## Yöntem notu — test sırası bağımsızlığı (tekrar eden ders)

İlk sürümde 5 test kırmızıydı ve bunu gerçek bir kırılma sanmak kolaydı.
Kök neden yine **paylaşılan ön kovaydı**: yük testi (4.7) `ucuz` sınıfında
100 jeton harcayınca sonraki testler 429 alıyordu.

Ön kova anahtarı `on:${istemciKimligi(req)}|${sinif}` biçiminde, yani
**her sınıfın ayrı ön kovası var**. Yük testi `sinyal` sınıfına taşındı ve
testler birbirinden yapısal olarak ayrıldı.

Bu, bu görevde **üçüncü kez** aynı sınıf bir tuzak oldu (matris, Faz 4,
ve daha önce Madde 55'teki hız sınırlayıcı). Ortak ders: **paylaşılan
durumu olan bir sistemi test ederken, testlerin birbirini kirletmemesi
tasarımla sağlanmalı** — sıralamayla değil.
