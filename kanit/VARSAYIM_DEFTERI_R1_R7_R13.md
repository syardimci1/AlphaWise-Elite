# VARSAYIM DEFTERİ — R-1 / R-7 / R-13

Her satır bir **varsayım** ve onun sınanma durumu. Sınanmamış varsayım,
kanıt değildir.

**Kapsam kararı (20.09.2026):** Seçenek **A** — Kapsam A değişmiyor.
`decision_log`/defter tek sistem hesabı kalıyor. **R-1 kapsam dışı.**
Sıra: R-7 → R-13.

---

## R-1 — neden kapsam dışı (varsayım değil, kayıtlı karar)

R-1'i kapatmak defteri kullanıcıya bölmeyi gerektirir. Risk kaydında
ölçülmüş bağımlılık şu: broker (Alpaca) tarafı da bölünmezse
`fark = defter_adet − broker_adet` her zaman ≤ 0 olur ve 01.09.2026'da
ölçülen 9,2 kat şişmiş K/Z kusuruna karşı konmuş güvenlik kapısı
**herkes için** işlevsizleşir. Yani R-1 tek başına yapılabilir bir iş
değildir. Kullanıcı Kapsam A'yı koruma kararı verdi; bu defterde
**açıkça açık** bırakılıyor.

---

## R-7 — varsayımlar ve sınanma durumu

| # | varsayım | sınandı mı | sonuç |
|---|---|---|---|
| V-7.1 | `/oz-iyilestirme/*` uçları sıradan kullanıcıya açık | **EVET** | **YANLIŞ.** Dördü de `yetki(x_admin_key)` çağırıyor; canlı anahtarsız çağrı `HTTP 401`. |
| V-7.2 | `PAPER_ADMIN_KEY` üretimde tanımlı | **EVET** | DOĞRU — 48 karakter. (İlk ölçümüm yanlış değişkeni sorguladı; bkz. Hata #1.) |
| V-7.3 | `yetki()` fail-closed | **EVET** | DOĞRU — `if not ADMIN_KEY or x_admin_key != ADMIN_KEY: raise 401`. Anahtar tanımsızsa da reddediyor. |
| V-7.4 | Hiçbir frontend bu uçlara proxy yapmıyor | **EVET** | DOĞRU, ama ilk ölçümüm eksikti (bkz. Hata #2). İki frontend var; ikisinde de `/oz-iyilestirme` beyaz listede **yok**. |
| V-7.5 | Servis dışarıdan erişilebilir | **EVET** | **YANLIŞ.** `127.0.0.1:8310`. Dış yüzeyde yalnızca 22 (ssh) ve 443 (stunnel→ssh) var. |
| V-7.6 | Servis tarafındaki kapı testle kilitli | **EVET** | **YANLIŞ — asıl boşluk buydu.** Proxy tarafı `test_proxy_salt_okunur.py` ile kilitliydi, servis tarafı değildi. `0bef966` ile kapatıldı. |

**R-7 sonucu:** iddia edilen risk ölçümle çürütüldü; gerçek boşluk
"kapı var ama testsiz" asimetrisiydi ve kapatıldı.

---

## R-13 — varsayımlar (FAZ 1 sürüyor)

| # | varsayım | sınandı mı | sonuç |
|---|---|---|---|
| V-13.1 | `godmode-execution` dışarıdan erişilebilir | **EVET** | **YANLIŞ.** `127.0.0.1:8030`. |
| V-13.2 | `/mode-a/execute` tarayıcıdan tetiklenebilir | **EVET** | **YANLIŞ.** Elite frontend'indeki `godmode/[ticker]` rotası **sabit** `/godmode/assessment/{ticker}` yoluna gider; ticker `encodeURIComponent` ile kodlanır, yol enjeksiyonu yok. |
| V-13.3 | Frontend admin anahtarını taşıyor | **EVET** | Bugün **HAYIR** — `GODMODE_ADMIN_KEY` frontend konteynerinde tanımsız, rota 503 döner. Anahtar tanımlanırsa rota çalışır ama yine yalnızca assessment yoluna. |
| V-13.4 | Emir yüzeyi ile okuma yüzeyi ayrı anahtarlar kullanıyor | **EVET** | **YANLIŞ — gerçek bulgu.** paper-trading'in `GODMODE_ADMIN_KEY`'i ile godmode-execution'ın `ADMIN_KEY`'i **aynı sır** (`sha256[:16]=7e02b48a6b016f45`). `PAPER_ADMIN_KEY` ayrı. |
| V-13.5 | `/mode-a/execute` tek başına emir gönderir | **EVET** | **YANLIŞ.** `confirm` varsayılanı `False` ve `if not confirm: return` ifadesi `submit_order`'dan **önce** (246<264, 373<408). Ayrıca piyasa kapalıysa `BLOCKED_MARKET_CLOSED`. |
| V-13.6 | Uç **gerçek para** emri gönderir | **EVET** | **YANLIŞ.** `paper=True` sabit kodlu, tek kurulum noktası (`main.py:24`). Alpaca **paper** hesabı. R-13'ün "kritik" derecesi bu ölçümle düşer. |
| V-13.7 | İki emir yüzeyi birbirinden bağımsız | **EVET** | **YANLIŞ — asıl bulgu.** Aynı Alpaca hesabı (PA30SBB6QS52); API anahtarlarının sha256'ları birebir aynı. |
| V-13.8 | Paylaşım pozisyon mutabakatını bozuyor | **EVET** | **HAYIR.** Tek yönlü karşılaştırma **bilinçli ve belgeli** (`main.py:980-982`); aynı sembolde çakışma yakalanır. (İlk yorumum yanlıştı — bkz. Hata #3.) |
| V-13.9 | Paylaşım boyutlandırmayı etkiliyor | **EVET** | **YANLIŞ — geri aldım.** Maruziyet ve boyutlandırma bilerek **defterden** türetiliyor (`main.py:767-774`), paylaşım altı yerde belgeli. İlk kaydım hatalıydı (bkz. Hata #4). |
| V-13.11 | Paylaşımın ele alınmamış bir köşesi var | **EVET** | **DOĞRU — R-15.** `zarar_durumu_belirle(pv, gerceklesen_kar)` payı defterden, paydayı paylaşılan hesaptan alıyor. Eşik 20.212 $, defterin bağlı sermayesi 9.876 $ → durdurma bu servis için pratikte tetiklenemez. Y1 + D3 → açık bırakıldı. |
| V-13.10 | Kapılar testle kilitli | **EVET** | **HAYIR — kapatılan boşluk buydu.** Dört test dosyasının hiçbiri `paper`/`verify_admin`/`confirm` doğrulamıyordu. `c8b3563` ile kapatıldı (13 test, 4 mutasyon). |
