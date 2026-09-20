# HATA HAFIZASI — R-1 / R-7 / R-13

Bu dosya, bu görev sırasında **kendi yaptığım** ölçüm ve akıl yürütme
hatalarını kaydeder. Amaç savunma değil, aynı hatanın tekrarını
engellemektir: her kayıt bir **önlem** ile biter.

---

## Hata #1: Ortam değişkeninin adını kodun içindeki değişken adıyla karıştırdım

| alan | içerik |
|---|---|
| **Madde** | R-7 |
| **Tarih** | 20.09.2026 |
| **Faz** | FAZ 1 (Ölç) |
| **Belirti** | `ADMIN_KEY tanimli mi: False` ölçtüm ve neredeyse *"paper-trading'in tüm admin yüzeyi herkese kapalı, operatör bile giremiyor"* diye raporlayacaktım. |
| **Kök neden (5 Whys)** | (1) Yanlış sonuç çıkardım → (2) çünkü yanlış ortam değişkenini sorguladım → (3) çünkü `os.getenv('ADMIN_KEY')` yazdım → (4) çünkü kodda gördüğüm **modül değişkeninin** adı `ADMIN_KEY` idi → (5) çünkü `ADMIN_KEY = os.getenv("PAPER_ADMIN_KEY", "")` satırında **sol taraf ile sağ tarafın farklı adlar** olduğunu okurken atladım. |
| **Düzeltme** | Doğru adla (`PAPER_ADMIN_KEY`) yeniden ölçtüm: tanımlı, 48 karakter. Ayrıca aynı komutta dört adayın (`PAPER_ADMIN_KEY`, `GODMODE_ADMIN_KEY`, `IZLENEN_LISTE_ANAHTARI`, `ADMIN_KEY`) hepsini birden yazdırdım. |
| **Tur** | 1 (ilk turda yakalandı) |
| **Tekrar** | Hayır |
| **Ders** | Canlı bir 401 yanıtı, anahtarın **tanımsız** olduğunu kanıtlamaz — anahtar tanımlıyken de anahtarsız çağrı 401 alır. İki ayrı olguyu tek gözlemle doğrulamaya çalıştım. |
| **Önlem** | Ortam değişkeni ölçerken **kod satırındaki `os.getenv(...)` argümanını** kopyala-yapıştır kullan, hafızadan yazma. Ve tek bir aday yerine ilgili adayların tamamını birden yazdır — yanlış ada düşmek imkânsızlaşır. |

Bu hata, Y3 (şüphecilik turu) sayesinde rapora girmeden yakalandı.

---

## Hata #2: "Tek bir frontend var" varsaydım; ikinci frontend'i kaçırdım

| alan | içerik |
|---|---|
| **Madde** | R-7 |
| **Tarih** | 20.09.2026 |
| **Faz** | FAZ 1 (Ölç) |
| **Belirti** | `grep -rn "8310\|godmode-paper\|PAPER_URL\|paper-trading" frontend/src` → **0 eşleşme** aldım ve *"frontend paper-trading'e proxy yapmıyor"* diye kaydettim. Gerçekte `godmode-paper-trading-service/frontend/src/app/api/paper/[...yol]/route.ts` diye tam da o işi yapan bir proxy var. |
| **Kök neden (5 Whys)** | (1) Yanlış olumsuz sonuç → (2) çünkü yalnızca `AlphaWise-Elite/frontend` ağacında aradım → (3) çünkü "frontend" deyince o dizini kastettiğimi varsaydım → (4) çünkü çalışma dizinim Elite deposu → (5) çünkü altyapıda **üç ayrı frontend** olduğunu doğrulamadan tek bir tanesini evrensel saydım. |
| **Düzeltme** | `find /opt/alphawise -maxdepth 3 -type d -name frontend` → üç sonuç: Elite, paper-trading, hizli-uyari. Doğru dosyayı bulup tam olarak okudum. |
| **Tur** | 1 |
| **Tekrar** | **EVET — bu hatanın sınıfı daha önce de yaşandı.** Kayıtlı hafızam zaten *"AlphaWise altyapısında bazı servisler bu reponun dışında, ayrı git repolarında yaşar — servis varlığını sadece bu repoyu grepleyerek sonuçlandırma"* diyor. Kural vardı, uygulamayı atladım. |
| **Ders** | Kural bilmek yetmiyor; **negatif bir bulgu** ("hiçbir yerde yok") üretirken kuralın tetiklenmesi gerekiyor. Pozitif bulgular kendini doğrular, negatif bulgular arama kapsamı kadar doğrudur. |
| **Önlem** | Bundan sonra "X hiçbir yerde yok" biçiminde bir sonuç yazmadan önce **arama kapsamını ayrıca yazdır** (hangi kök dizinler tarandı) ve kapsam tek depo ise `/opt/alphawise` geneline genişlet. Kapsamı yazdırmak, dar aramayı görünür kılar. |

---

## Hata #3: Bir güvenlik kapısını "kör" ilan ettim; kod yorumu beni yalanladı

| alan | içerik |
|---|---|
| **Madde** | R-13 |
| **Tarih** | 20.09.2026 |
| **Faz** | FAZ 1 (Ölç) |
| **Belirti** | Mutabakat ucu defterde **1**, broker'da **12** pozisyon görüp `tutarli: True` dönünce *"ayrışma varsa emir gönderme kapısı kör"* dedim. Bu, bir güvenlik kapısını işlevsiz ilan eden ağır bir iddiaydı. |
| **Kök neden (5 Whys)** | (1) Yanlış iddia → (2) çünkü çıktıdan davranışı çıkarsadım → (3) çünkü uygulamayı okumadan yorumladım → (4) çünkü 1≠12 farkı "hata" olarak o kadar bariz göründü ki doğrulama ihtiyacı hissetmedim → (5) çünkü **bariz görünen bulgular** için şüphecilik turunu atlama eğilimim var. |
| **Düzeltme** | `src/main.py:980-982` okundu. Karşılaştırma tek yönlü ve bu **açıkça belgeli**: *"YALNIZCA defterin iddia ettigi semboller. Paper hesap PAYLASIMLI: godmode/execution ayni hesaba baska semboller yaziyor, onlarin bu defterde olmamasi hata DEGILDIR."* Aynı sembolde çakışma olsaydı kapı yakalardı. İddiayı derhal düzelttim. |
| **Tur** | 1 |
| **Tekrar** | Hayır |
| **Ders** | Şüphecilik turu en çok, bulgu **çarpıcı** olduğunda gereklidir — çünkü çarpıcı bulgu, doğrulama isteğini azaltır. Bir davranışı çıktıdan çıkarsamak, uygulamayı okumanın yerini tutmaz. |
| **Önlem** | Bir güvenlik mekanizmasını "işlevsiz/kör/etkisiz" diye nitelemeden önce **o mekanizmanın kaynağını oku ve yorum satırlarını da oku** — tasarımcı bilinçli bir ödünleşmeyi çoğu zaman oraya yazmış olur. |

Bu düzeltme sonucunda gerçek bulgu daha da değerli hâle geldi: asıl örtüşme
pozisyon karşılaştırmasında değil, **boyutlandırma tabanında** (`portfolio_value`).

---

## Hata #4: "Belgelenmemiş" dedim; aslında altı yerde belgeliydi

| alan | içerik |
|---|---|
| **Madde** | R-13 |
| **Tarih** | 20.09.2026 |
| **Faz** | FAZ 1 → kapanış (commit'lendikten **sonra** yakalandı) |
| **Belirti** | Paylaşılan broker hesabını *"belgelenmemiş bir bağlantı"* ve *"pozisyon boyutlandırması %73,3'ü başkasına ait bir tabandan türüyor"* diye kaydettim ve **bu hâliyle commit ettim** (`f967ca1`). İkisi de yanlıştı. |
| **Kök neden (5 Whys)** | (1) Yanlış iddia → (2) çünkü `pv`'nin ne için kullanıldığını doğrulamadan "boyutlandırma" dedim → (3) çünkü beş çağrı yerini `grep` ile bulup **bağlamlarını okumadım** → (4) çünkü sayı (%73,3) çarpıcıydı ve anlatıyı kendi başına taşıyor gibi göründü → (5) çünkü **Hata #3'ün dersini bir kez daha uygulamadım**: çarpıcı bulgu, doğrulama isteğini azaltıyor. |
| **Düzeltme** | Beş çağrı yerinin bağlamı okundu. Ölçülen gerçek: maruziyet ve boyutlandırma **bilerek defterden** türetiliyor (`main.py:767-774`), paylaşım **altı ayrı yerde** belgeli (343, 681-699, 731-738, 740-744, 767-774, 980-982) ve ekip aynı sayıyı (`73.575`) 02.09.2026'da zaten ölçmüş. İddia geri alındı; yerine çok daha dar ve doğrulanmış bir gözlem kondu (R-15: `zarar_durumu_belirle`'de pay defterden, payda paylaşılan hesaptan). Commit düzeltildi. |
| **Tur** | 2 |
| **Tekrar** | **EVET — Hata #3 ile aynı kök**: çıktıdan/grep'ten davranış çıkarsamak. İkinci kez oldu. |
| **Ders** | Aynı kök neden iki kez tekrarladığına göre sorun dikkat değil **yöntem**. `grep` bir konum bulur, **bağlam bulmaz**. Bir değişkenin "ne için kullanıldığı" sorusunun cevabı, tanımının değil **kullanım yerinin** bağlamındadır. |
| **Önlem** | Bir değişkene rol atfetmeden (`pv` = "boyutlandırma tabanı") önce, bulunan her kullanım yerinin **en az 6 satırlık bağlamını** oku. Ve "X belgelenmemiş" demeden önce, X'in adını/eşanlamlılarını ilgili dosyada **ayrıca** ara — bu vakada `paylasimli` araması altı yeri tek komutta çıkarırdı. |

Bu hata, diğer üçünden farklı olarak **commit edildikten sonra** yakalandı.
Bu yüzden yalnızca düzeltilmedi, aynı zamanda `f967ca1` commit metni de
düzeltildi — yanlış bir tespitin sürüm geçmişinde kalıcılaşmaması için.

---

## Hata #5 (KÖK NEDEN) — `grep` bu ortamda `.gitignore`'a uyuyor

| alan | içerik |
|---|---|
| **Madde** | R-16 / sır döndürme |
| **Tarih** | 20.09.2026 |
| **Faz** | ölçüm (tekrar eden) |
| **Belirti** | `/opt/alphawise` kökünden yapılan **her** özyinelemeli arama boş dönüyordu. Beş kez "X hiçbir yerde yok" sonucu ürettim; en az ikisi yanlıştı. |
| **Kök neden** | Bu ortamda `grep` GNU grep **değil**, `ugrep`'i `--ignore-files` bayrağıyla saran bir **kabuk fonksiyonu**. `--ignore-files`, `.gitignore` dosyalarına uyar. `/opt/alphawise/.gitignore` ise beyaz liste mantığındadır ve ilk kuralı `/*` — yani **her şeyi yoksayar**. Sonuç: ağacın neredeyse tamamı taranmadan atlanıyor, komut **0,069 saniyede** boş dönüyor. |
| **Neden fark edilmedi** | 0 sonuç, "yok" ile "bakılmadı" arasında ayrım yapmaz. Alt dizinlerden (`…/godmode-paper-trading-service`) yapılan aramalar çalıştığı için araç sağlam görünüyordu. |
| **Düzeltme** | `command grep` (fonksiyonu atlayıp gerçek GNU grep'i çağırır) ya da `find … -print0 \| xargs -0 grep`. Doğru araçla arandığında `GODMODE_ADMIN_KEY`'i sunan **iki ek yer** bulundu (paper-trading'in kendi frontend'i ve bir araç betiği) — dar aramada görünmüyorlardı. |
| **Tur** | 5 (aynı sınıf hata beşinci kez) |
| **Ders** | Hata #2 ve #4'ün "pozitif kontrol yap" dersi **doğruydu ama yetersizdi**: pozitif kontrol hatayı *gösteriyordu*, ben ise her seferinde aramayı biraz değiştirip devam ediyordum. Asıl gereken, **aracın neden böyle davrandığını** bulmaktı. Semptomu beş kez tedavi ettim, nedeni bir kez aradım ve bulundu. |
| **Önlem** | Bu depoda ağaç geneli arama için **her zaman** `command grep` ya da `find+xargs`. Pozitif kontrol başarısız olursa aramayı değiştirmeden **önce aracı sorgula**. |

---

## Yöntem notu — bu beş hatanın ortak yanı

İkisi de **yanlış olumsuz** üretti ve ikisi de "ölçtüm" kılığındaydı. Bir
komut çalıştırmış olmak, doğru şeyi ölçtüğüm anlamına gelmiyor. Y9 "kanıtsız
iddia yasak" diyor; bu iki olay ona bir ek getiriyor:

> **Kanıtın kendisi de denetlenmelidir: ölçtüğüm şey, iddia ettiğim şey mi?**

Pratik karşılığı: bir ölçüm olumsuz sonuç verdiğinde, ölçüm aracının
**olumlu** bir durumda gerçekten sinyal ürettiğini de göster (pozitif
kontrol). Testlerde mutasyon neyse, ölçümde pozitif kontrol odur.
