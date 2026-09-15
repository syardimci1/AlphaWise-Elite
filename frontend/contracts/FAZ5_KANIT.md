# FAZ 5 — Dağıtım: Kanıt Dosyası

## Ön-koşul kontrolü
`docker ps` ile nginx/traefik/caddy/envoy/haproxy arandı — **HİÇBİRİ
çalışmıyor**, gerçek trafik-bölme altyapısı YOK (middleware.ts'in
kendi belgelediği "GÜVENİLİR BİR VEKİL YOK" bulgusuyla tutarlı). Bu
yüzden canary %5 ADIMI ATLANDI; onun yerine whitelist/preview-token
mekanizması (C5) kullanılabilir hale getirildi — ama bu dağıtımda
AKTİF EDİLMEDİ (aşağıya bkz., "Aktivasyon kararı").

## Kill switch
`KOYFIN_EVENT_OVERLAY_ENABLED` docker-compose.yml'de `environment:`
altında (build-time NEXT_PUBLIC_ değil, runtime — bkz. C5). Kapatma
mekanizması AÇMA mekanizmasıyla AYNI (`docker compose up -d --no-deps
frontend`) — bu dağıtımın kendisinde bu komutun süresi ÖLÇÜLDÜ: **10,61
saniye** (aşağıya bkz.). Bu, Bölüm 1'in ≤15sn SERT eşiğinin altında
ama Faz 5 metninin "10sn içinde" ifadesine göre SINIRDA — dürüstlük
için gizlenmiyor.

## Dağıtım ve kesinti ölçümü
```
docker compose build frontend   # 108,5s (kullanici trafigini ETKILEMEDI - eski konteyner calismaya devam etti)
docker compose up -d --no-deps frontend
```
Sürekli `/` sağlık taraması (yaklaşık 25ms aralıklarla, 733 örnek):
**ÖLÇÜLEN KESİNTİ PENCERESİ: 10,610 saniye.**

## Kanıt (hepsi)
- Eski sayfalar hâlâ 200: `/` → 200, `/dashboard` → 200 (dağıtım
  sonrası curl ile doğrulandı).
- `alphawise-frontend`: `Status=running Health=healthy`.
- Diğer servisler (örn. `alphawise-congress-trading`) DOKUNULMADI:
  `RestartCount=0`, `StartedAt` değişmedi.
- Konteynerin GERÇEK ortam değişkenleri doğrulandı (`docker exec ...
  printenv`): `KOYFIN_EVENT_OVERLAY_ENABLED=0`,
  `KOYFIN_PREVIEW_TOKEN=` (boş) — yani olay katmanı şu an HİÇBİR
  kullanıcı için görünür DEĞİL, tamamen hareketsiz durumda.
- p95 render canlıda ayrıca ölçülmedi (flag kapalı olduğu için
  canlıda hiç render TETİKLENMİYOR) — laboratuvar ölçümü (135ms/500
  olay, bkz. FAZ2_KANIT.md) geçerliliğini koruyor.
- Hata oranı artışı: middleware/servis logları bu dağıtımdan sonra
  ayrıca izlenmedi (canlı bir log-tarama altyapısı bu görevin
  kapsamında kurulmadı) — AÇIKÇA eksik bırakılan bir madde.

## Rollback komutu (yazılı, YÖNTEM olarak daha önce bu depoda KANITLI — bu oturumda CANLI REHEARSAL yapılmadı)
```
cd /opt/alphawise/commercial/AlphaWise-Elite
git log --oneline -- frontend | head -20   # koyfin-overlay commit'lerini bul
git revert <ilk-koyfin-commit>..<son-koyfin-commit> --no-commit
docker compose build frontend
docker compose up -d --no-deps frontend
```
Bu AYNI build+recreate mekanizması bu oturumda 2 kez (sec-edgar-13f
madde 58 ve bu dağıtım) başarıyla kullanıldı — yöntem kanıtlı. Ancak
"geri al" komutu GERÇEKTEN production'da DENENMEDİ (kasıtlı - canlı
sistemi yalnızca tatbikat için bozmak, riski azaltmak yerine
artırırdı). Bu dürüstçe açık bırakılıyor.

## Aktivasyon kararı — flag "0" bırakıldı, %100'e AÇILMADI

Master prompt "sonra %100" diyor ama bu oturumda BİLİNÇLİ olarak
YAPILMADI. Gerekçe: bu ortamda gerçek bir Supabase oturumu
kurulamadığı için (bkz. FAZ2_KANIT.md, `/dashboard` kimlik doğrulama
arkasında), `EventOverlayLayer`'ın 4 gerçek veri kaynağını GERÇEK
kimlik doğrulamalı bir oturumda uçtan uca çekmesi bu oturumda HİÇ
gözlemlenemedi (yalnızca `fetch` mock'lanarak izole test edildi, bkz.
FAZ2_KANIT.md). Kod-yolu ayrı ayrı kanıtlı (normalize/marker/tıklama/
performans/sıfır-maliyet) ama "gerçek oturumla gerçek 4 API'den canlı
veri" birleşik senaryosu YOK. Bu boşluk kapanmadan TÜM kullanıcılara
açmak, bu görevin kendi "kanıtsız iddia etme" ilkesine aykırı olurdu.
Kod GÜVENLE dağıtıldı (varsayılan kapalı, sıfır davranış değişikliği,
her an geri alınabilir) — AKTİVASYON KARARI kullanıcıya bırakılıyor.

## Çıkış kararı
Kod dağıtımı PASS (kesinti ≤15sn sert eşiği geçti, eski davranış
değişmedi, diğer servisler etkilenmedi). Özellik aktivasyonu BİLİNÇLİ
olarak ERTELENDİ — bu bir FAIL değil, ölçülmüş bir risk kararı.
