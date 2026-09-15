# Çoklu Kullanıcı İzolasyonu — Varsayım Defteri

**Tarih:** 15 Eylül 2026

Bu defter, çalışmanın dayandığı ve **yanlış çıkarsa sonucu değiştirecek**
varsayımları listeler. Her biri için: nasıl doğrulandığı, ya da neden
doğrulanamadığı yazılıdır. Doğrulanmamış bir varsayımı "ölçüldü" diye
saymak, bu belgenin engellemek istediği tek şeydir.

---

## V-1 — İzole ortam üretimi temsil ediyor

**Durum: DOĞRULANDI (ama önce YANLIŞTI — bkz. HATA_HAFIZASI H-1)**

İzole ortamın ACL'i üretimden okunarak birebir eşitlendi:

```
profiles = user_portfolios = {postgres=arwdDxtm, anon=arwdDxtm,
                              authenticated=arwdDxtm, service_role=arwdDxtm}
user_portfolios_id_seq     = {postgres=rwU, anon=rwU, authenticated=rwU, service_role=rwU}
```

`auth.uid()` ve `auth.role()` fonksiyonları üretimden `pg_get_functiondef`
ile **birebir** kopyalandı; yeniden yazılmadı.

**Kalan fark:** üretim PostgreSQL **17.6**, izole ortam **17.11**. Aynı ana
sürüm, dolayısıyla ACL ve RLS anlamı aynıdır. Yama sürümü farkının bu
davranışları değiştirdiğine dair bir belirti yok, ama **aynı sürüm değildir**
ve bu bir varsayımdır.

## V-2 — `anon` anahtarı gerçekten herkese açık

**Durum: DOĞRULANDI (kod okunarak)**

`frontend/src/lib/supabase.ts`, tarayıcı istemcisini
`NEXT_PUBLIC_SUPABASE_ANON_KEY` ile kuruyor. `NEXT_PUBLIC_` önekli her değer
Next.js tarafından tarayıcı paketine gömülür. Dolayısıyla `anon` rolünün
yetkileri **kamuya açık** yetkilerdir. Üç açığın da kritikliği bu gerçeğe
dayanıyor.

## V-3 — Bu iki tabloyu hiçbir kod kullanmıyor

**Durum: DOĞRULANDI (arama ile), ama TEK BİR DEPODA**

`from('profiles')` ve `from('user_portfolios')` araması tüm frontend ve
backend'de boş döndü. Üç `createClient()` çağrısının üçü de yalnızca kimlik
işlemi yapıyor (`signInWithPassword`, `getUser`, `signOut`). `service_role`
hiçbir yerde kullanılmıyor.

**SINIR:** bu arama yalnızca `AlphaWise-Elite` deposunda yapıldı. AlphaWise
altyapısında bazı servisler **ayrı git depolarında** yaşıyor. Bu tabloları
başka bir depodaki bir servisin kullanma olasılığı **dışlanmadı**. Y6 açısından
risk düşüktür (o servis `service_role` kullanıyorsa yetkileri zaten
dokunulmadı), ama sıfır değildir.

## V-4 — Yetki daraltması meşru kullanımı kesmiyor

**Durum: DOĞRULANDI (olumlu denetimle)**

"Her şey reddedildi" bir başarı değil, kullanıcının kendi verisini
yönetememesi olurdu. Bu yüzden her test ağına **olumlu denetim** kondu ve
göçün kendi doğrulama sorgusuna iki olumlu satır eklendi:

- A kendi `full_name` / `company_name` değerini değiştirebiliyor → 1 satır
- A kendi portföyünü ekleyebiliyor / adlandırabiliyor / silebiliyor → 1 satır
- `auth_profil_duzenleyebilir_OLMALI_4` → **4**
- `auth_portfoy_yazabilir_OLMALI_4` → **4**

## V-5 — `authenticated` sequence USAGE'ına ihtiyaç duyuyor

**Durum: DOĞRULANDI (ölçülerek)**

`user_portfolios.id` bir `serial`; varsayılanı `nextval(...)`. Bu varsayılan,
INSERT sırasında **çağıran rolün** yetkisiyle değerlendirilir. `authenticated`'ın
USAGE'ı alınsaydı kullanıcı kendi portföyünü oluşturamazdı (Y6 ihlali). Bu
yüzden yalnızca `anon`'dan alındı; olumlu denetimde `authenticated` nextval'in
hâlâ çalıştığı ölçüldü.

## V-6 — Geri alma göçü üretim durumuna döner

**Durum: DOĞRULANDI (gidiş-dönüş testiyle)**

İleri → geri → ileri → geri turu çalıştırıldı; her "geri", ACL parmak izini
üretimdekiyle **aynı** değere döndürdü (`ce34b400d78a3a69`). Parmak izi
`aclexplode()` ile **küme** olarak hesaplanıyor, dizge olarak değil (bkz.
HATA_HAFIZASI H-3).

Geri almanın açıkları **gerçekten geri açtığı** da ölçüldü: geri alma
sonrasında `anon` yeniden TRUNCATE edebiliyor. Bu, dosyadaki "bu bir onarım
değil, acil durum çıkışıdır" uyarısının doğru olduğunun kanıtıdır.

## V-7 — Göç veriyi değiştiremez

**Durum: DOĞRULANDI (hem ölçüm hem statik kanıt)**

- Ölçüm: göç öncesi ve sonrası satır sayıları + içerik özeti aynı.
- Statik: göç dosyasında **hiç DML/DDL yok**; kullanılan SQL komutları
  `BEGIN, COMMIT, GRANT, REVOKE, SELECT` ile sınırlı. Veri değiştirmesi
  fiziksel olarak mümkün değil.

## V-8 — RLS politikalarının kendisi doğru

**Durum: DOĞRULANDI ama DEĞİŞTİRİLMEDİ**

21 satır düzeyi test 006 ÖNCESİNDE de geçiyordu. Politikalara bilinçli olarak
dokunulmadı: çalışan bir şeyi değiştirmek, öncesi/sonrası karşılaştırmasını
bozardı.

**Not:** `profiles` üzerindeki UPDATE politikasında açık bir `WITH CHECK` yok.
PostgreSQL bu durumda `USING` ifadesini `WITH CHECK` olarak da kullanır, yani
davranış doğrudur — ama bu **örtük** bir davranışa dayanmaktır ve politika bir
gün elle düzenlenirse sessizce değişebilir. 006 bunu kolon yetkisiyle ikinci
bir katmana bağladı (`id` kolonu artık yazılamıyor).

## V-9 — `service_role` ve `postgres` yetkilerine dokunulmaması doğru

**Durum: GEREKÇELENDİRİLDİ, ölçülmedi**

İkisi de zaten BYPASSRLS taşıyor; onlardan yetki almak güvenlik kazancı
sağlamaz, ama Supabase Studio ve yönetim araçlarını bozabilir. Bu bir
**karar**, bir ölçüm değil.

## V-10 — Üretim veri tabanı çizgisi

**Durum: ÜRETİMDEN OKUNDU (salt okuma)**

`profiles` = 2 satır, `user_portfolios` = 1 satır, `auth.users` = 2 satır.
Y6'nın "mevcut 2 profil kayıp yaşamaz" koşulunun sayısal karşılığı budur.

**SONUÇ (15.09.2026, göç uygulandıktan sonra ölçüldü):** üç sayı da aynı
kaldı ve profil içerik özeti (`583d6743a512781cf63281925aa3f09a`) değişmedi.
Varsayım doğrulandı, artık bir varsayım değil bir ölçümdür.
