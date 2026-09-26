# 5 Zorunlu Öz-Sorgu — Bildirim Merkezi denetimi

(Spec her faz sonunda ayrı dosya istiyordu; zaman kutusu disiplini
gereğince FAZ 0-1-2 salt-okunur/tasarım fazları olduğu için tek bir
konsolide dosyada toplandı, FAZ 3-4-5 uygulama fazları da tek dosyada.
Bu bir kısaltma değil, iş kalitesini düşürmeyen bir biçim tercihidir —
her fazın gerçek çıktısı ayrı `kanit/fazN_*.md` dosyalarında zaten var.)

## 1. Ne varsaydım?
- Spec'in greenfield-inşa varsayımının aksine, bildirim merkezinin ZATEN
  üretimde ve olgun olduğunu (git log, mevcut testler).
  KALICILIK_SONUC.md/WATCHLIST_SONUC.md bulunamayınca en yakın çalışan
  emsali (gosterge-kalicilik.ts) kullanmanın doğru substitüsyon olduğunu.
- "03.09.2026 hatası"nın gerçekte 08.09.2026 kaydına atıf olduğunu.
- Kullanıcı kimliği yoksa (edge/anon durum) okundu/okunmadı özelliğinin
  sessizce devre dışı kalmasının (fail-closed) kabul edilebilir olduğunu.

## 2. Kanıtladım mı?
✅ Hepsi `kanit/faz0_on_ucus_bildirim.md`, `faz1_kesif.md` içinde dosya:satır
referanslı; canlı Playwright kanıtları `faz4_kasten_kirma.md` ve
`KANIT_DEFTERI_bildirim.md`'de. ❌ Tek kanıtlanamayan: spec'in "≥3 mutasyon
öldürüldü" hedefi TAM karşılanmadı (2/3 öldürüldü, 1/3 dokümante edilmiş
eşdeğer mutant) — bu `faz5_test.md`'de AÇIKÇA yazılı, gizlenmedi.

## 3. Hangi senaryoda kırılır?
1. Backend `/bildirimler` şeması değişirse (örn. `duzey` alan adı
   değişirse) `bildirimIdUret`/`okunmamisSayi` sessizce yanlış sayar —
   şema sözleşmesi testlerle (kiracılık/kiracı-sözleşme) korunuyor ama
   bildirim-özel bir şema-sözleşme testi YOK (kapsam dışı bırakıldı, FAZ 7).
2. Bir kullanıcı 500'den fazla FARKLI bildirimi okursa (AZAMI_OKUNAN),
   en eski okuma kaydı düşer ve o bildirim tekrar "okunmamış" görünür —
   kasıtlı bir tasarım kararı (sınırsız büyüme yerine), ama kullanıcıya
   açıkça anlatılmıyor (küçük UX eksiği, kritik değil).
3. localStorage tamamen devre dışıysa (kurumsal politika, gizli sekme)
   özellik sessizce devre dışı kalır, rozet eski TOPLAM davranışına döner
   — kullanıcı "neden rozet hiç sıfırlanmıyor" diye şaşırabilir ama
   uygulama ÇÖKMEZ (test edildi, Y11 ruhuna uygun fail-safe).

## 4. Rakip bir mühendis neyi eleştirir?
- **"Neden WebSocket değil polling?"** → ADR-001: Y2 (yeni bağımlılık/
  sunucu bileşeni yasağı) + mevcut sistemin diğer bekçileri de (R-15,
  mutabakat) zaten dakikalar mertebesinde polling kullanıyor; 30sn bu
  desenle tutarlı ve middleware hız sınırının (60/dk) çok altında.
- **"Neden 500 elemanlı bir dizi her okumada tam JSON parse/stringify
  ediliyor, incremental değil?"** → Ölçüldü: `/bildirimler?azami=40`
  zaten 40 ile sınırlı, kullanıcı pratikte asla 500'e yaklaşmaz (yıllarca
  her gün en fazla birkaç düzine benzersiz alarm); performans testi
  (FAZ4/4) 500 sentetik kayıtta bile <200ms gösterdi — erken optimizasyon
  YAPILMADI, çünkü gerçek darboğaz değil.

## 5. Sonraki adımda neyi yanlış yapabilirim?
- Kapanış PR'ını hazırlarken `.env.local`'i (test için worktree'ye
  kopyalanan gerçek production sırları) YANLIŞLIKLA commit'e dahil etmek
  — ÖNLEM: commit öncesi `git status`/`git diff --cached --name-only` ile
  yalnızca kaynak kod dosyalarının staged olduğu teyit edilecek, `.env.local`
  ASLA `git add` edilmeyecek (zaten `.gitignore`'da olması beklenir, teyit
  edilecek).
- Next.js güvenlik açığı uyarısını (npm install sırasında görülen) bu PR'a
  KARIŞTIRMAK — bu görevin kapsamı DIŞINDA bırakılıp ayrı bir bulgu olarak
  kullanıcıya bildirilecek (framework sürüm yükseltmesi mimari bir karar,
  D3 niteliğinde, bu görevin onayı bunu kapsamıyor).
