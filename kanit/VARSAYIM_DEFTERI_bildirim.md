# VARSAYIM_DEFTERI — Bildirim Merkezi denetimi

| # | Varsayım | Kanıt | Durum |
|---|---|---|---|
| 1 | `KALICILIK_SONUC.md`/`WATCHLIST_SONUC.md` bulunamadığında en yakın emsal `gosterge-kalicilik.ts`'tir | Depo genelinde `find -iname` ile arandı, 0 sonuç; `gosterge-kalicilik.ts` aynı ad alanı desenini (`kullaniciId`) kullanıyor ve 24.09.2026'da canlı doğrulanmış | ✅ Kabul edildi, ADR-004'ün temeli |
| 2 | Spec'in "03.09.2026 hatası" aslında `toplayici.py`/`bildirim-ozet.js` içinde 3 ayrı yerde belgelenen 08.09.2026 bayat-alarm hatasıdır | Tarih farkı var ama belirti tanımı (bayat alarmın güncel görünmesi, mutabakat örneği) birebir örtüşüyor; depoda "03.09" ile eşleşen tek kayıt alakasız bir konu (dark pool tarih gösterimi, FAZ2_KANIT.md) | ✅ Kabul edildi, FAZ 1'de gerekçeli |
| 3 | Bildirim id'si için `(kaynak,zaman,mesaj)` üçlüsü yeterli kararlılıkta bir anahtardır | `toplayici.py`'nin kendi `tekille()` fonksiyonu ZATEN aynı üçlüyü tekillestirme anahtarı olarak kullanıyor (satır 143-164) — sunucu tarafında kanıtlanmış aynı varsayım | ✅ Kabul edildi |
| 4 | Kullanıcı kimliği alınamazsa (kullaniciId=null) okundu/okunmadı özelliğinin sessizce devre dışı kalması (fail-closed, rozet eski TOPLAM davranışına döner) doğru tercihtir | `GrafikTerminali.tsx`'in aynı `/api/config/kimlik` ucuna karşı fail-closed davranışıyla (çizim YÜKLENMEZ) tutarlı — depodaki yerleşik "kiracı izolasyonu sert ilkedir" kuralı | ✅ Kabul edildi |
