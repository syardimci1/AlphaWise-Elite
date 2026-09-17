# FAZ 1.4 — Kimlik Akışı Mimarisi (ölçülen BUGÜNKÜ hâl + önerilen hedef)

Bu şema FAZ 3.0'ın otomatik senaryo üretiminde **girdi** olarak kullanılacak.

## A) BUGÜN — kimliğin nerede kaybolduğu

```
                    ┌──────────────────────────────────────────────────┐
  TARAYICI ────────▶│ ELITE FRONTEND (alphawise-frontend)               │
  (Supabase JWT)    │                                                  │
                    │  middleware.ts                                    │
                    │   ├─ hız sınırı   → kova anahtarı = 'ortak' ◀──✗ KULLANICI YOK
                    │   │                  (middleware.ts:135-147)      │
                    │   └─ oturumDogrula() → { kullaniciId } ◀── ÜRETİLİYOR
                    │                         :255-256                  │
                    │                              │                    │
                    │                              ▼                    │
                    │                        ✗ ATILIYOR ───────────────┼── KOPUŞ NOKTASI
                    │                                                  │
                    │  route.ts / servisProxy ──── başlık YOK ─────────┼──▶ servisler
                    │   (servis-proxy.ts:40-60: tipte header alanı yok) │
                    └──────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────────┐
  TARAYICI ────────▶│ PAPER-İZLEME FRONTEND (godmode-paper-izleme)      │
  (tek parola)      │  oturum.ts:30-33 — kodun KENDİ ifadesi:           │
                    │   "SAGLAMAZ: KULLANICI BAZLI kimlik.              │
                    │    Tek paylasilan sir vardir; 'kim giris yapti'   │
                    │    sorusunu yanitlayamaz."                        │
                    │  çerez = <sonaErme>.<tuz>.<hmac>  ◀── içinde kimlik YOK
                    └──────────────────────────────────────────────────┘
```

### Aşağı akış — beş HTTP yüzeyi, hepsinde kimlik yok

```
  ELITE /api/*  ──┬──▶ alphawise-maa:8000 ........... decision_log (user_id YOK)
                  │      └ /memory/{t} → cognee dataset "alphawise_decisions" ◀── TEK GLOBAL
                  ├──▶ alphawise-portfoy:8000 ....... defter.sqlite (ro) — filtre YOK
                  ├──▶ alphawise-godmode-execution .. ★ GERÇEK EMİR (submit_order :264,:408)
                  ├──▶ alphawise-bildirim ........... sistem log dosyaları
                  └──▶ 17 piyasa verisi servisi ..... kullanıcıdan bağımsız (doğru)

  PAPER-İZLEME ───▶ godmode-paper-trading:8000 ...... X-Admin-Key (tek paylaşılan)
  CRON (curl) ────▶ godmode-paper-trading:8000 ...... X-Admin-Key
  HEDEF-PLANLAYICI▶ godmode-paper-trading:8000 ...... X-Tarihsel-Anahtar (dar)
```

**Ortak veri tabanı — iki servis, tek dosya, tek broker:**

```
   godmode-paper-trading  ──(rw)──┐
                                  ├──▶  /veri/defter.sqlite   journal_mode=delete
   alphawise-portfoy      ──(ro)──┘      karar / islem / sinyal_gozlem  (user_id YOK)

   godmode-paper-trading  ──┐
                            ├──▶  TEK Alpaca paper hesabı  ◀── ★ ÇELİŞKİNİN KAYNAĞI
   godmode-execution      ──┘       (ALPACA_PAPER_API_KEY tekil)
```

## B) ÖNERİLEN HEDEF — kimlik kenarda zorlanır

```
  TARAYICI ──JWT──▶ middleware.ts
                      └─ oturumDogrula() → kullaniciId
                           │
                           ├──▶ hız sınırı kovası: `${kullaniciId}:${sinif}`   [C3-a]
                           │
                           └──▶ x-kullanici-id başlığı  ◀── EKLENEN TEK SATIR GRUBU
                                     │
                                     ▼
                        servisProxy(… , kullanici)          [servis-proxy.ts, KORUMASIZ]
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
  portfoy-service            MAA proxy rotası            raporlar rotası
  defter.py: WHERE user      önbellek anahtarına         dizin: /reports/<user>/
  [KORUMASIZ]                kullanıcı eklenir           [KORUMASIZ]
                             [KORUMASIZ]

        ▼ (ayrı süreç, ASGI sarmalayıcı — main.py'ye DOKUNMADAN)
  godmode-paper-trading
    src/kullanici.py  → anahtar/JWT → ContextVar          [YENİ, KORUMASIZ]
    Dockerfile CMD: src.main:app → src.kullanici:app      [KORUMASIZ, emsal: backtest_api]
    defter.py baglanti() → ContextVar'dan YOL türetir     [KORUMASIZ]
      └─ /veri/defter_<kullanici>.sqlite
         ⚠ main.py:906/1015'teki ham SQL kendiliğinden doğru kapsamda çalışır
         ⚠ AMA main.py:544/640/721/744 broker mantığı KIRILIR (bkz. risk R-1)
```

## C) Ölçülen kopuş noktaları (FAZ 3 senaryolarının kaynağı)

| # | kopuş | dosya:satır | düzeltme korumasız mı |
|---|---|---|---|
| K-1 | middleware `kullaniciId`'yi üretip atıyor | `middleware.ts:255-256` | ✅ evet |
| K-2 | `servisProxy` tipi başlık kabul etmiyor | `servis-proxy.ts:40-49` | ✅ evet |
| K-3 | hız sınırı kovası `'ortak'` | `middleware.ts:135-147` | ✅ evet |
| K-4 | MAA proxy önbelleği/havuzu YOL anahtarlı | `maa/[...yol]/route.ts:78,100,167` | ✅ evet |
| K-5 | cognee dataset'i tek global | `maa/src/main.py:1082` | ❌ **KORUNAN** |
| K-6 | `/api/raporlar/[dosya]` `_req`'i kullanmıyor | `raporlar/[dosya]/route.ts:17-20` | ✅ evet |
| K-7 | portfoy-service filtresiz okuyor | `portfoy-service/src/defter.py:33-35` | ✅ evet |
| K-8 | paper-izleme oturumu kullanıcı bilmiyor | `frontend/src/lib/oturum.ts:30-33` | ✅ evet |
| K-9 | godmode-execution tek global ADMIN_KEY | `godmode/execution/src/main.py:27-30` | ✅ evet |
| K-10 | kota sayacı API anahtarı başına | `gamma-exposure-service/main.py:117` | ✅ evet |
| K-11 | defterde ham SQL korunan dosyada | `godmode .../main.py:906,1015` | ❌ **KORUNAN** (yol bazlı kiracılıkla aşılır) |
| K-12 | broker mantığı (mutabakat/risk tavanı) | `godmode .../main.py:544,640,721,744` | ❌ **KORUNAN, aşılamaz** |
| K-13 | `DELETE FROM user_portfolio` filtresiz | `maa/src/main.py:127` | ❌ **KORUNAN** (tablo yaratılmazsa zararsız) |

**10 kopuşun 10'u korumasız dosyalarda. Üçü korunan dosyalarda; biri (K-12)
dışarıdan aşılamıyor.**
