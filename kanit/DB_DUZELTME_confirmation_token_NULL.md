# DB düzeltmesi — `auth.users` NULL token sütunları (24.09.2026)

## Sorun

GoTrue (Supabase auth), `confirmation_token`/`recovery_token`/
`email_change_token_new`/`email_change` sütunları `NULL` olan kullanıcılarda
çöküyor: `sql: Scan error on column index 3, name "confirmation_token":
converting NULL to string is unsupported`. `POST /token` (parola ile giriş)
ve `POST /admin/generate_link` bu yüzden `500` dönüyor. Log kanıtı:
`supabase-auth` konteynerinde bu hata en az 22 Ağustos 2026'dan beri kayıtlı
— **PR #2 ile ilgisi yok**, ondan önce var olan bir altyapı hatası.

## Kapsam

Yalnızca iki test hesabı, yalnızca gerçekten `NULL` olan sütunlar:

| id | email |
|---|---|
| `c59c7853-b752-44ca-b40d-c4eb09798b50` | `selcuk@alphawise.test` |
| `d7e28a7c-d217-4abd-8fa5-ddc93d869d60` | `partner@alphawise.test` |

Düzeltme öncesi: her iki satırda da 4 sütun (`confirmation_token`,
`recovery_token`, `email_change_token_new`, `email_change`) `NULL`.

## Uygulanan SQL (tek transaction, satır sayısı doğrulamalı)

```sql
BEGIN;
DO $$
DECLARE affected int;
BEGIN
  UPDATE auth.users SET
    confirmation_token = COALESCE(confirmation_token, ''),
    recovery_token = COALESCE(recovery_token, ''),
    email_change_token_new = COALESCE(email_change_token_new, ''),
    email_change = COALESCE(email_change, '')
  WHERE id IN ('c59c7853-b752-44ca-b40d-c4eb09798b50','d7e28a7c-d217-4abd-8fa5-ddc93d869d60')
    AND (confirmation_token IS NULL OR recovery_token IS NULL
         OR email_change_token_new IS NULL OR email_change IS NULL);
  GET DIAGNOSTICS affected = ROW_COUNT;
  IF affected <> 2 THEN
    RAISE EXCEPTION 'Beklenmeyen etkilenen satir sayisi: % (beklenen 2)', affected;
  END IF;
END $$;
COMMIT;
```

Etkilenen satır sayısı beklenenle (2) eşleşmeseydi `RAISE EXCEPTION`
transaction'ı otomatik `ROLLBACK` ederdi (bir kez böyle oldu — ilk denemede
kontrol mantığı yanlış statement'ın `ROW_COUNT`'una bakıyordu, `affected=0`
bulundu, istisna fırlatıldı, transaction hiç `COMMIT` edilmeden geri alındı;
bu, sorgu sonrası `SELECT` ile iki satırın da hâlâ `NULL` olduğu doğrulanarak
teyit edildi). Düzeltilmiş kontrolle ikinci denemede `affected=2` çıktı ve
`COMMIT` edildi.

## Sonuç (COMMIT sonrası doğrulama)

```
id                                    email                    ct_null rt_null ectn_null ec_null
c59c7853-b752-44ca-b40d-c4eb09798b50  selcuk@alphawise.test   f       f       f         f
d7e28a7c-d217-4abd-8fa5-ddc93d869d60  partner@alphawise.test  f       f       f         f
```

## Geri alma

Bu düzeltme sütunları `NULL`'dan `''` (boş string) yapar; GoTrue zaten hiçbir
zaman bu alanları `NULL` yazmıyor (yalnızca eski/manuel eklenmiş satırlarda
NULL görülüyor), yani ileri yönde bu sütunlara asıl uygulama tarafından bir
daha `NULL` yazılmayacaktır — geri almak fonksiyonel olarak gerekmez. Yine de
istenirse:

```sql
BEGIN;
UPDATE auth.users SET
  confirmation_token = NULL,
  recovery_token = NULL,
  email_change_token_new = NULL,
  email_change = NULL
WHERE id IN ('c59c7853-b752-44ca-b40d-c4eb09798b50','d7e28a7c-d217-4abd-8fa5-ddc93d869d60');
COMMIT;
```

## Etki alanı

Yalnızca bu iki satır değişti — başka hiçbir `auth.users` satırına
dokunulmadı (WHERE `id IN (...)` ile açıkça sınırlı, `UPDATE 2` çıktısı bunu
doğruluyor).
