# FAZ 0 — Ön-Uçuş (Bildirim Merkezi denetimi)

## 0.1 Zorunlu okuma — durum

| # | Kaynak | Bulundu mu | Not |
|---|---|---|---|
| 1 | CLAUDE.md | ✅ | Korunan dosyalar: `maa/src/cascade.py`, `maa/src/main.py`, `maa/src/llmquant_client.py`. Bütçe onay kuralı, dil kuralları, karar kodları — bu görevle doğrudan kesişmiyor (bildirim merkezi LLM/kredi harcamıyor, karar kodu üretmiyor). |
| 2 | bildirim-service kodu (port 8350) | ✅ | `bildirim-service/src/main.py` + `toplayici.py`. FastAPI, `/health`, `/kaynaklar`, `/bildirimler`. 6 kaynaktan (otonom_bekci, haftalik_egitim, godmode_paper×2, oz_iyilestirme, r15_gecis) okur, tekiller, bayatlık işaretler, özet üretir. |
| 3 | olay-tarayici ALARM formatı | ✅ | `olay-tarayici-service/src/bildirim.py` — bu WhatsApp/whapi bildirim gönderimi, bildirim-service'in kaynağı DEĞİL. Gerçek ALARM formatı `toplayici.py` içinde: `[zaman] mesaj` (köşeli log) + JSONL, `duzey ∈ {kritik, alarm, uyari, bilgi}`. |
| 4 | KALICILIK_SONUC.md | ❌ BULUNAMADI | Depo genelinde arandı (`find -iname`), sonuç yok. **VARSAYIM**: en yakın gerçek emsal `frontend/src/lib/grafik/gosterge-kalicilik.ts` (24.09.2026'da doğrulanmış, kullanıcı+sembol ad alanlı localStorage deseni: `alphawise:grafik:gosterge:v1:<uid>:<SEMBOL>`). Bu emsal S4/Y10 tasarımında referans alınacak. |
| 5 | WATCHLIST_SONUC.md | ❌ BULUNAMADI | Depoda watchlist özellikli kod da yok (`grep -rl watchlist` boş sonuç). Aynı VARSAYIM #4 geçerli. |
| 6 | middleware.ts | ✅ | `frontend/src/middleware.ts` — hız sınırlama + oturum zorunluluğu, `/api/*` için tek nokta. Kimlik doğrulama ayrıca `frontend/src/app/api/bildirimler/route.ts` içinde `rolKapisi()` ile İ-6/R-9 deseniyle rol bazlı kapı olarak UYGULANMIŞ DURUMDA (VARSAYILAN_ROLLER=['admin','partner']). |
| 7 | "03.09.2026 hatası" (bayat alarm güncel görünmesi) | ⚠️ TARİH FARKI | Depoda bu spesifik hata **08.09.2026** tarihli olarak kayıtlı (`bildirim-ozet.js`, `toplayici.py` içindeki çoklu yorum: "canli kullanimda bulundu, 08.09.2026" — mutabakat alarmının bir hafta önce kapanmış olmasına rağmen listenin başında ACIK gibi görünmesi). `FAZ2_KANIT.md` içindeki tek "03.09" eşleşmesi alakasız bir konuya (dark pool/13F tarih gösterimi) ait. **VARSAYIM**: spec'teki "03.09.2026" bu 08.09.2026 olayına atıf yapıyor (yakın tarih, aynı belirti tanımı: bayat alarmın güncel görünmesi). Bu hata zaten `bayatlik_isaretle()` (toplayici.py:167) ve `bayatlikMetni()` (bildirim-ozet.js:94) ile ÇÖZÜLMÜŞ ve commit `81c3dd2` ("Madde 28 duzeltmesi") ile production'da.

## 0.2 Keşif — özet bulgular

- Bildirim merkezi ZATEN ÜRETİMDE ve commit geçmişi olgun: `08d5d60` (ilk kurulum) → `81c3dd2` (bayatlık düzeltmesi) → `314ee74`/`04bf9be` (kiracılık/rol kapısı) → `a404fd8` (R-15 bağlantısı) → `52de275`/`b12b3d8` (yetkisiz rolde tam gizleme).
- Gerçek mimari spec'in varsaydığından FARKLI ve daha olgun:
  - **C1 (tek doğruluk kaynağı)**: spec'in önerdiği gibi tarayıcıdan doğrudan `http://localhost:8350` DEĞİL — `frontend/src/app/api/bildirimler/route.ts` üzerinden proxy (`servisProxy()`), `BILDIRIM_URL=http://alphawise-bildirim:8000` (konteyner içi ağ adı, 8350 dışarıya haritalı port olabilir). Doğrudan tarayıcı→backend bağlantısı CORS'suz zaten çalışmaz ve middleware/kiracılık desenini atlar.
  - **ADR-001 (polling vs WebSocket)**: zaten polling — ama aralık spec'in "30sn" varsayımından farklı olabilir, `BildirimMerkezi.tsx`'te doğrulanacak (FAZ 1).
  - **ADR-002 (24s bayatlık eşiği)**: GERÇEK mekanizma zaman eşiği DEĞİL, olgusal "bu alarmdan sonra aynı kaynaktan N normal kayıt geldi mi" sayacı (`sonraki_normal_kayit`). Bu, 08.09.2026 hatasını zaman eşiğinden DAHA DOĞRU çözüyor: bir alarm 25 saat önce olsa bile hâlâ çözülmediyse "geçmiş" sayılmamalı; süre bazlı eşik bunu yanlış sınıflandırırdı.
  - **Y8 (kimlik ad alanı / kullanıcı bazlı sızıntı)**: içerik kullanıcıya özel DEĞİL, sistem işletim kaydı (tmux pane pid, claude oturum yeniden başlatma vb.) — `route.ts` içindeki yorum bunu açıkça "Çapraz-kullanıcı sızıntısı DEĞİL" diye belgeliyor. Gerçek hassasiyet sınırı ROL bazlı (admin/partner görür, user görmez), kullanıcı bazlı değil. Bu, spec'in Y8/S4 tasarımını (x-user-id header + kullanıcı ad alanlı bildirim) YANLIŞ öncülden hareket ettiriyor — düzeltilecek varsayım.
- **GERÇEK EKSİK (spec'in Y10/S4'üyle örtüşen, gerçekten doğrulanmış boşluk)**: okundu/okunmadı (read/unread) kalıcılığı HİÇ YOK. `BildirimMerkezi.tsx` içinde "okundu" kelimesi yalnızca kaynak durumu anlamında geçiyor (`kaynakEtiketi`), bildirim bazlı okundu/okunmadı state'i, sayaç, localStorage anahtarı yok. Rozet sayısı (`rozetSayisi`) her zaman kritik+alarm toplamını gösteriyor — kullanıcı zaten görmüş olsa bile rozet sıfırlanmıyor.

## 0.3 Çakışma kontrolü

```
$ git branch --show-current
feature/coklu-kullanici-izolasyon
$ git status --porcelain | wc -l
30+ (başka oturumlardan kalma commit'lenmemiş değişiklik ve izlenmeyen dosya)
```
Kural gereği (kirli ağaç → sorma, izole worktree): `origin/main` (f827ca7) üzerinden `feature/bildirim-merkezi` dalıyla izole worktree kuruldu:
`/tmp/.../scratchpad/bildirim-izole`. Ana çalışma dizinine DOKUNULMADI.

## 0.4 Taban çizgisi

Korunan dosya hash'leri (`kanit/faz0_korunan_hashler_taban.txt`, origin/main@f827ca7):
```
b96a2865a520a3802f18ef45fa7b61056cc4279f8f97c602fa8d3529a09a147a  maa/src/cascade.py
6e9f429d4e94713161f169f4a2e7259754ca6800d86a5139a8177963babca32a  maa/src/main.py
29ce43b29bed4e19464193cfa449f463a80b5ac322aa0e9a05997eefbbccde9b  maa/src/llmquant_client.py
```
Bu görev bu dosyalara dokunmayacak (bildirim/sunum katmanı, karar üretim mantığıyla ilgisi yok — Y1/Y4).

## Çıkış Kapısı

✅ Okuma tamam (2 kaynak bulunamadı, en yakın emsalle telafi edildi ve VARSAYIM_DEFTERI'ne yazılacak)
✅ Keşif kanıtlı (yukarıda dosya:satır referanslarıyla)
✅ Çakışma kontrolü yapıldı, izole worktree kuruldu
✅ Korunan dosya hash'leri kayıtlı

→ FAZ 1'e geçiliyor.
