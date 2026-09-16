# Çoklu Kullanıcı İzolasyonu — Hata Hafızası

Her kayıt: **ne oldu · kök neden · düzeltme · tekrar sayısı · ders**.
Kural (0.3): aynı hata 2. kez → strateji katmanı değiştir. 3. kez → DUR-SOR.

---

## H-1 — Taban çizgisini kendi dizinimi yarattıktan SONRA aldım

**Faz:** 0 · **Tekrar:** 1

**Ne oldu.** "Başkasının işi" taban çizgisini (`git status` anlık görüntüsü)
`kanit/` dizinini oluşturduktan sonra aldım. Sonuç: `?? kanit/` taban
çizgisine girdi ve "bu görevin dosyaları" ölçümü **kendi dosyalarımı
göremez** hâle geldi (55 girdi, 0 kendi dosyam).

**Kök neden.** Ölçüm aracını, ölçeceği durumu değiştirdikten sonra kalibre
ettim.

**Düzeltme.** Taban çizgisinden `kanit/` çıkarıldı (54 girdi); ölçüm artık
`?? kanit/` döndürüyor.

**Ders.** Bir taban çizgisi, ölçüm yapan tarafın hiçbir izi oluşmadan
**önce** alınmalıdır.

---

## H-2 — "Cognee gerçek bir sızıntı" iddiam yanlıştı

**Faz:** 1 → 2 · **Tekrar:** 1

**Ne oldu.** Faz 1 raporunda `/api/maa/memory/{ticker}` ucunu
"tarayıcıdan çapraz-kullanıcı karar geçmişi — gerçek bir sızıntı" diye
bildirdim. Faz 2'de cognee'ye **ne yazıldığını** okuyunca yanlış olduğu
çıktı (`maa/src/main.py:634-638`):

```
"Hisse senedi sembolu {ticker} ({company_name}, sektor: {sector}) icin
 {decision} karari verildi (skor: {total_score}). Katman skorlari: {scores}."
```

Metinde **hiçbir kullanıcı boyutu yok** — saf ticker analizi. Kapsam A'da
(defter tek sistem hesabı) kararlar zaten sistem kararıdır, dolayısıyla
sızacak kullanıcı verisi **yoktur**.

**Kök neden.** Ucun *erişilebilirliğini* (beyaz listede olması) ölçtüm ama
*içeriğini* ölçmedim. "Kullanıcı verisine ulaşılabiliyor" sonucuna,
verinin kullanıcıya ait olduğunu doğrulamadan vardım.

**Düzeltme.** Faz 2'de düzeltildi; İ-5 kalemi "sızıntı kapatma"dan çıkarılıp
**ileriye dönük risk** olarak yeniden sınıflandırıldı: defter ileride
kullanıcıya bölünürse (Kapsam B/C) bu **gerçek** bir sızıntıya dönüşür ve
dataset adı korunan dosyada **hem yazma (`:641`) hem okuma (`:1082`)**
ucundan kilitli olduğu için kenarda tam çözülemez.

**Ders.** "Erişilebilir" ≠ "kullanıcıya ait". Bir sızıntı iddiası, verinin
**içeriğinin** kullanıcıya özgü olduğu gösterilmeden kurulamaz.

---

## H-3 — Başkasının izlenmeyen dosyasını sildim

**Faz:** 2 · **Tekrar:** 1 · **Ağırlık: en ciddisi**

**Ne oldu.** `npx tsc` ve `npm test` çalıştırdıktan sonra dizinde
`package-lock.json` ve `tsconfig.tsbuildinfo` gördüm, ikisini de "kendi
araç artefaktım" sayıp sildim. `tsconfig.tsbuildinfo` gerçekten benimdi
(bugün 21:04). Ama **`package-lock.json` 15 Eylül 14:21 tarihliydi** ve
Faz 0 taban çizgisinin **26. satırında** duruyordu — yani başka bir
oturuma ait, dokunmamam gereken bir dosyaydı.

**Kök neden.** Silmeden önce taban çizgisine bakmadım. Elimde tam da bunun
için kurulmuş bir çapa vardı ve **kullanmadım**. Zaman damgasını ancak
sildikten sonra fark ettim.

**Düzeltme.** İki aşamalı:
1. `npm install --package-lock-only` ile yeniden üretmeyi denedim → 26.936
   bayt çıktı, orijinal 55.104 baytdı; **birebir değildi**, yetersizdi.
2. Çalışan `alphawise-frontend` konteynerinde `/app/package-lock.json`
   bulundu (55.104 bayt, aynı tarih). `docker cp` ile geri yüklendi;
   **SHA-256 konteynerdekiyle birebir aynı** (`18dafb8ba02545bb…`).

**Kalıcı önlem (asıl düzeltme).** Hatanın kendisinden daha önemlisi,
koruma mekanizmamın bunu **yakalamamış** olmasıydı: `benim_dosyalarim.sh`
yalnızca çakışma desenine uyan **beş** dosyanın hash'ini doğruluyordu;
taban çizgisindeki diğer 49 girdiden birinin silinmesi fark edilmiyordu ve
betik ben sildikten sonra da "PASS" demeye devam ediyordu.

Betiğe **2b bölümü** eklendi: taban çizgisindeki her izlenmeyen dosyanın
hâlâ var olduğu doğrulanıyor. Düzeltme **mutasyon testiyle sınandı** —
dosya geçici olarak silinince `*** EKSIK ***` verdi, geri konunca `PASS`.

**Ders.** Bir koruma mekanizması kurmak yetmez; **neyi kapsamadığı**
ölçülmelidir. Benimki "değişiklik"i kapsıyordu, "yokluk"u kapsamıyordu —
ve gerçekleşen tam olarak yokluktu. Ayrıca: bir dosyayı silmeden önce
**zaman damgasına ve taban çizgisine bakmak** bir refleks olmalı.

---

## H-4 — Test koşum yolu iki ayrı nedenden bozuktu

**Faz:** 2 · **Tekrar:** 1

**Ne oldu.** `npm test` yalnızca `tests/koyfin/*.test.ts` glob'unu
çalıştırıyordu; `tests/` kökündeki **10 dosya / 106 test** hiç koşmuyordu.
Glob'u genişletmeye çalıştım, iki tuzağa ardı ardına düştüm:

1. `node --test 'tests/**/*.test.ts'` → `Could not find ...`.
   **Neden:** `node --test`'in kendi glob desteği **v21+**; buradaki Node
   **v20.20.2**. Tırnak içindeki deseni kabuk da genişletmiyor, Node da.
2. `node --import tsx --test tests/*.test.mjs tests/*/*.test.ts` → **6 kırmızı**
   ve toplam test sayısı 129'dan 49'a düştü.
   **Neden:** `--import tsx` aktifken tsx `src/lib/*.js` dosyalarını
   dönüştürüyor ve adlandırılmış dışa aktarımları kayboluyor
   (`does not provide an export named 'aramaAkisiBaslat'`). Aynı testler
   tsx **olmadan** 106/106 geçiyor.

**Düzeltme.** İki grup **ayrı** koşuluyor, her biri kendi yükleyicisiyle:
```
node --test tests/*.test.mjs && node --import tsx --test tests/*/*.test.ts
```
Sonuç: **144/144** (106 + 38).

**Ders.** İkisi de "araç varsayımı" hatasıydı: birincide sürüm özelliğini,
ikincide yükleyici yan etkisini varsaydım. Düzeltmeden önce **mevcut
testlerin yeşil olduğunu ayrı ayrı ölçmek** ikisini de erken yakaladı.

---

## H-5 — Doğrulama sırasında tsconfig'i geri alıp kendi derlememi bozdum

**Faz:** 2 · **Tekrar:** 1

**Ne oldu.** İ-2'yi doğrulamak için `npx next build` çalıştırdım. Build
başarısız oldu ve **her seferinde farklı bir rotada**
(`/api/config/koyfin-flag`, sonra `/api/finra-darkpool-regsho`, sonra
`/_not-found`). "Compiled successfully" diyip sonra
`PageNotFoundError: Cannot find module for page` veriyordu.

Değişikliklerimin kırdığı sonucuna vardım ve bunu izole etmek için
üç ayrı deneme daha yaptım — biri çalışma ağacımdaki 16 rota
değişikliğini kazara **geri aldı** (`git checkout -- frontend/src/`,
çünkü ADIM 0+1'i zaten commit'lemiştim, yani HEAD benim kodumu içeriyordu).

**Kök neden.** `next build`, `tsconfig.json`'ın `include` listesine
`.next/types/**/*.ts` ekliyor. Ben her denemeden sonra "istenmeyen
değişiklik" sanıp `git checkout -- frontend/tsconfig.json` ile geri
alıyordum. Sonraki derleme, o girdiye ihtiyaç duyan `.next` tip
dosyalarıyla tutarsız bir tsconfig görüp çöküyordu. Yani **başarısızlığı
ben üretiyordum.**

**Düzeltme.** tsconfig'e dokunmadan tek bir temiz tur çalıştırıldı:
`✓ Compiled successfully` + `✓ Generating static pages (13/13)`.
İ-2 derlemeyi kırmıyor.

**Ders.** Bir aracın kendi ürettiği dosyayı "istenmeyen değişiklik" diye
geri almadan önce, o dosyanın aracın çalışması için **gerekli** olup
olmadığı sorulmalı. Ayrıca: hata mesajı her denemede değişiyorsa bu
genellikle kodun değil, **ortamın** belirsiz olduğunun işaretidir.

---

## BULGU (hata değil) — deponun `tsconfig.json`'ı yerel `next build` ile uyumsuz

Ölçüldü: deponun commit'li `tsconfig.json`'ında `include` listesinde
`.next/types/**/*.ts` **yok** ve o hâliyle temiz bir `next build`
`/_not-found` üzerinde **başarısız oluyor**. `next build` her çalıştığında
bu girdiyi kendisi ekliyor.

Docker'da fark edilmemesinin nedeni ölçüldü: `frontend/Dockerfile`
`RUN npm run build` çalıştırıyor ve konteynerdeki `tsconfig.json`'da
girdi **VAR** (`include: ['**/*.ts','**/*.tsx','next-env.d.ts','.next/types/**/*.ts']`,
`plugins: [{name:'next'}]`). Yani değişiklik imaj katmanında kalıyor,
depoya hiç dönmüyor.

**Bu görevde DEĞİŞTİRİLMEDİ** (kapsam dışı, başkasının kararı). Ama
yerel derleme yapacak olan, ya `next build`'in tsconfig'i değiştirmesine
izin vermeli ya da öncesinde `rm -rf .next` yapmalıdır.

---

## Ortak örüntü (H-1, H-3, H-4, H-5)

Beşin dördünde sorun **koda değil, araca/ölçüme** aitti — bu, önceki
görevde dört kez tekrarlanan örüntünün aynısı. Bu görevde alınan yapısal
karşı önlem: her ölçüm aracının kendisi **mutasyon testiyle** sınanıyor
(AST hash'i 4 mutasyonla, silinme denetimi 1 mutasyonla doğrulandı).
