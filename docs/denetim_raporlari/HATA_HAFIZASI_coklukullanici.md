# Çoklu Kullanıcı İzolasyonu — Hata Hafızası

**Tarih:** 15 Eylül 2026

Bu çalışma sırasında **dört hata** yapıldı (H-1..H-4): üçü benim kendi
kodumda/testimde, biri göçün kendisinde. Hepsi yakalandı ve düzeltildi.
Burada yazılmalarının nedeni, ikisinin **sessizce yanlış bir "güvenli"
raporuna** yol açabilecek türden olmasıdır.

Beşinci kayıt (H-5) bir hata değil, testin bulduğu **önceden var olan bir
üretim hatasıdır**; buraya konmasının nedeni taşıdığı iki derstir. Altıncısı
(H-6), göç üretime uygulandıktan **sonra** ortaya çıkan bir ölçüt eskimesidir.

---

## H-1 — İzole ortam üretimi temsil etmiyordu (EN CİDDİSİ)

**Ne oldu:** İzole doğrulama ortamının tablo ACL'i üretimden birebir
kopyalanmamıştı. Üretimde `anon=arwdDxtm`, izole ortamda `m` (MAINTAIN)
**hiç yoktu**.

**Neden tehlikeliydi:** Testler "her şey kapalı" diyordu, ama hiç var olmayan
bir yetkiyi test etmemişlerdi. Göç üretime uygulansaydı `anon` MAINTAIN'i
**korurdu** ve `VACUUM FULL`/`REINDEX` ile tabloyu ACCESS EXCLUSIVE kilitle
herkese kapatabilirdi. Yani "kapattım" raporu doğru, ama **eksik** olacaktı.

**Nasıl yakalandı:** Geri alma göçünü yazmak için üretimin gerçek ACL'i
okundu; okunan dizgedeki `m` harfi izole ortamda yoktu.

**Düzeltme:** İzole ortamın ACL'i üretimle birebir eşitlendi, **tüm taban
çizgisi ve tüm test ağı sıfırdan yeniden çalıştırıldı**, MAINTAIN sömürüsü
ölçülerek doğrulandı ve göçe 7. bölüm eklendi.

**Ders:** "İzole ortam kurdum" demek yetmez. Ortamın temsil ettiği iddiası
**ölçülmelidir** — tercihen hedef sistemden okunan bir parmak iziyle. Bir
testin geçmesi, doğru şeyi test ettiği anlamına gelmez.

---

## H-2 — `REVOKE UPDATE (role)` hiçbir şey yapmıyordu

**Ne oldu:** Ayrıcalık yükseltmeyi kapatmak için göçe yalnızca
`REVOKE UPDATE (role) ON public.profiles FROM anon, authenticated;` yazıldı.
Bu ifade **sessizce etkisizdir**: PostgreSQL'de TABLO düzeyi bir UPDATE
yetkisi TÜM kolonları kapsar ve kolon düzeyi bir REVOKE ondan eksiltme yapamaz.

**Nasıl yakalandı:** Göçün kendi doğrulama sorgusu
`role_kolonu_update_yetkisi | 1` döndürdü (0 bekleniyordu) ve bypass testi
"A KENDİ role'unu 'admin' yapabildi" demeye devam etti. Yani **göç "başarılı"
raporladı ama doğrulama yalan söylemedi.**

**Düzeltme:** Önce tablo düzeyi UPDATE tamamen alındı, sonra yalnızca izin
verilen kolonlara kolon düzeyi UPDATE verildi:

```sql
REVOKE UPDATE ON public.profiles FROM anon, authenticated;
GRANT UPDATE (email, full_name, company_name, updated_at)
    ON public.profiles TO authenticated;
```

`id` bilerek dışarıda bırakıldı — kullanıcı kendi satırının kimliğini
değiştirememeli. Bu, beklenmedik bir yan kazanç olarak satır sahipliği
çalmayı da kapattı.

**Ders:** Bir REVOKE'un **yazılmış olması** çalıştığı anlamına gelmez. Her
göçün, iddiasını sayısal olarak sınayan bir doğrulama sorgusu olmalı — ve o
sorgu `0` yerine `1` dediğinde bu bir başarısızlık olarak okunmalı.

---

## H-3 — ACL karşılaştırması sıraya duyarlıydı (yanlış BAŞARISIZ)

**Ne oldu:** Geri alma testinde ACL'ler `relacl::text` dizgesi olarak
karşılaştırıldı. `relacl` bir **dizidir** ve eleman sırası yetkilerin veriliş
sırasını yansıtır:

```
üretim      : {postgres=…, anon=…, authenticated=…, service_role=…}
geri alma   : {postgres=…, authenticated=…, service_role=…, anon=…}
```

Küme aynı, sıra farklı. Test, **sağlam çalışan** bir geri almayı "BOZUK"
gösterdi (2 FAIL).

**Düzeltme:** Karşılaştırma `aclexplode()` ile satırlara açılıp sıralı bir
küme olarak yapıldı. Aynı hata **geri alma göçünün kendi doğrulama
sorgusunda da** vardı (dizgeyi sabit bir metinle kıyaslıyordu) — o da küme
karşılaştırmasına çevrildi. Düzeltmeden sonra 8/8.

**Ders:** H-2'nin tersi yönde bir hata: orada test fazla hoşgörülüydü, burada
fazla katı. İkisi de aynı kökten — **ölçütün kendisi doğrulanmamıştı**. Bir
FAIL gördüğümde ilk sorulacak soru "kod mu bozuk, yoksa ölçüt mü?" olmalı.

---

## H-4 — Testin kendi girdisi eksikti (yanlış BAŞARISIZ)

**Ne oldu:** Olumlu denetim testi `user_portfolios`'a `tickers` kolonunu
vermeden INSERT denedi; `tickers` NOT NULL olduğu için
`null value in column "tickers"` hatası aldı. Çıktıda bu, bir güvenlik
engeli gibi göründü.

**Düzeltme:** Teste `tickers` değeri eklendi. Güvenlik bulgusu değildi.

**Ders:** Bir testin RED alması "engellendi" demek değildir; **neden** RED
aldığı okunmalıdır. Hata metnini okumadan sonucu sınıflandırmak, bu çalışmada
iki kez yanlış sonuca götürdü (H-3 ve H-4).

---

## H-5 — Olumlu denetim, aranmayan bir üretim hatasını buldu

**Ne oldu:** Bu bir hata *yapmak* değil, bir hatayı *bulmak*. Üretimde meşru
kullanımın bozulmadığını ölçen olumlu denetim beklenmedik biçimde kırmızıya
döndü: `duplicate key value violates unique constraint "user_portfolios_pkey"`.

Kök neden 006 değildi. `user_portfolios_id_seq`, tabloda `id=1` satırı
dururken `is_called=f` durumundaydı; yani portföy oluşturan **ilk gerçek
kullanıcı** çakışma hatası alacaktı. Göç sequence'e yalnızca `REVOKE`
uyguluyor — bu yetki alır, değer değiştirmez — ve aynı çakışma 006'dan
bağımsız olarak izole ortamda da yeniden üretildi.

**Beklenmedik yan etki:** PostgreSQL'de `nextval` **işlem dışıdır**. Testin
INSERT'i başarısız olup geri alındığı hâlde sayacı ilerletti ve hatayı fiilen
giderdi. Yani `ROLLBACK`, üretimde "hiçbir iz bırakmaz" anlamına gelmez.

**Ders — iki tane:**

1. *"Her şey engellendi" testi yarım bir testtir.* Bu hatayı bulan şey saldırı
   denemesi değil, **meşru kullanımın hâlâ çalıştığını** sınayan denetimdi.
   Yalnızca reddedilmeyi ölçen bir ağ, bu hatayı asla göremezdi.
2. *`ROLLBACK` her şeyi geri almaz.* Sequence değerleri, `NOTIFY`, dosya
   yazımı ve harici çağrılar işlem dışıdır. Üretimde "güvenli çünkü geri
   alıyorum" derken bu istisna akılda tutulmalıdır.

## H-6 — Canlı üretimi "taban" sayan test, üretim değişince yanlış oldu

**Ne oldu:** Geri alma testi, hedef durumu **canlı üretimden okuyordu**:
"geri alma sonrası ACL, üretimdekiyle aynı olmalı." Bu, göç uygulanana kadar
doğruydu. 006 üretime uygulandığı an üretim artık "006 öncesi" değil "006
sonrası" durumu gösterir oldu ve test, **hiç değişmemiş, sağlam çalışan** bir
geri almayı 3 FAIL ile bozuk raporladı.

İkinci deneme de yanlıştı: hedef elle sabitlendi, ama `information_schema`'nın
tablo yetkilerinden **türettiği** kolon satırları (`KOL:...`) atlandı; eksik
taban yine yanlış FAIL üretti.

**Düzeltme:** Taban artık `01_uretim_acl_esitle.sql` çalıştırılarak
**üretilir**. Bu döngüsel değildir: o dosya yetkileri açık `GRANT`'larla
kurar, geri alma göçü ise **bağımsız bir yoldan** aynı duruma dönmek
zorundadır. İkisinin aynı parmak izini vermesi anlamlı bir testtir.

Aynı turda üçüncü bir ölçüt eskimesi daha çıktı: `goc_testi.py`,
`git grep "def karar_uret"` ile canlı karar yolunu arıyordu ve **kendisi**
o dizgeyi içerdiği için kendini buluyor, kendi düzenlenmesini "canlı yol
değişti" diye raporluyordu.

**Ders:** Bir testin tabanı, testin **doğruladığı şeyden bağımsız** ve
**zamanla kaymayan** bir kaynaktan gelmelidir. Canlı bir sistemi hem
değiştirip hem de referans almak, testi ilk başarılı değişiklikte yalancı
yapar. Bu, H-3'ün aynı kökten üçüncü tekrarıdır: **kod doğruydu, ölçüt
yanlıştı.**

## Ortak ders

Kaydedilen altı maddenin dördünde sorun **koda değil, ölçüme** aitti
(H-1, H-3, H-4, H-6). Bu çalışmada
güvenliği sağlayan şey RLS politikaları değil, **her iddianın karşı-ölçümle
sınanmasıydı**: "kapattım" dedikten sonra saldırıyı tekrar denemek, "geri
alınabilir" dedikten sonra gerçekten geri alıp açığın yeniden açıldığını
görmek, "ortam temsil ediyor" dedikten sonra parmak izini hedeften okumak.

Kapatılmamış bir açığı bulmak, kapandığını sanmaktan iyidir.
