# SIR DÖNDÜRME PLANI — paylaşılan `ADMIN_KEY` (`7e02b48a…`)

**Tarih:** 20 Eylül 2026 · **Durum:** ⏸ plan hazır, **uygulanmadı**
**Ön koşul:** R-16 dar anahtar ayrımı ✅ uygulandı (`285970b` + `0418269`)

---

## Neden hâlâ gerekli

R-16 ile emir yüzeyi ayrıldı: paylaşılan `ADMIN_KEY` artık **emir
gönderemiyor**. Ama hâlâ üç serviste ortak ve şunları açıyor:

- `godmode-execution`'ın **tüm okuma uçları** (`/account` dahil — hesap
  bakiyesi, alım gücü, pozisyonlar)
- `alphawise-oanda`'nın **tamamı**

Yani birinin ortamını okuyan biri, diğerinin okuma yüzeyini de açar.
Döndürme, bu yanal geçişi kapatır.

---

## Taşıyıcılar — KESİN liste (iki yöntemle doğrulandı)

| konteyner | değişken | rolü | kaynak dosya |
|---|---|---|---|
| `alphawise-godmode-execution` | `ADMIN_KEY` | **doğrular** (gelen isteği) | `godmode/execution/.env` |
| `godmode-paper-trading` | `GODMODE_ADMIN_KEY` | **sunar** (giden çağrıda) | `godmode-paper-trading-service/.env` |
| `alphawise-oanda` | `ADMIN_KEY` | **doğrular** (kendi kapısı) | `oanda-service/.env:14` |

> **Düzeltme.** Önceki notumda `supabase-rest` ve `alphawise-phoenix`'in de
> bu değişkenleri taşıdığını yazmıştım — **yanlıştı**. O ölçüm
> `docker exec … sh -c` ile yapılmıştı ve bu iki konteynerde `sh`
> bulunmadığı için komut başarısız oluyordu; çıkan değeri gerçek anahtar
> sanmışım. `docker inspect .Config.Env` ile bakıldığında ikisinde de
> `ADMIN_KEY`/`GODMODE_ADMIN_KEY` **hiç yok** (0 eşleşme).

**Taşımayanlar** (doğrulandı, plana dahil değil):
`godmode-paper-izleme` ve Elite frontend — ikisinde de `GODMODE_ADMIN_KEY`
tanımsız, `godmode/[ticker]` rotaları bugün `503` dönüyor.

---

## İki BAĞIMSIZ döndürme

Bunlar birbirine bağlı değildir; biri yapılıp diğeri ertelenebilir.

### Döndürme A — godmode çifti (birlikte hareket etmek ZORUNDA)

`godmode-execution` doğrulayan, `godmode-paper-trading` sunan taraftır.
Biri değişip diğeri değişmezse okuma çağrıları `401` alır.

**Pencere riski ölçüldü:** son 24 saatte `godmode-execution`'a gelen
**18** istek — 12'si kendi healthcheck'i, 6'sı bugünkü doğrulamalarım.
Yani **organik trafik sıfır**. İki recreate arasındaki ~10 saniyelik
pencere pratikte risksiz.

Yine de otomasyon penceresinden kaçınılmalı: kâğıt işlem cron'u hafta içi
**16, 18, 20, 21** saatlerinde çalışıyor (`godmode_paper_otomasyon.sh`).

```bash
# 0) YEDEK (depo disina)
mkdir -p /opt/alphawise/yedekler
cp /opt/alphawise/godmode/execution/.env \
   /opt/alphawise/yedekler/godmode_execution.env.rot_$(date +%Y%m%d_%H%M%S)
cp /opt/alphawise/godmode-paper-trading-service/.env \
   /opt/alphawise/yedekler/paper_trading.env.rot_$(date +%Y%m%d_%H%M%S)

# 1) YENI SIR (tek kez uretilir, IKI dosyaya AYNI deger yazilir)
YENI=$(openssl rand -hex 24)

# 2) IKI dosyada da degistir  (ADMIN_KEY ve GODMODE_ADMIN_KEY ayni degeri alir)
#    godmode/execution/.env           -> ADMIN_KEY=$YENI
#    godmode-paper-trading-service/.env -> GODMODE_ADMIN_KEY=$YENI

# 3) ONCE dogrulayan, SONRA sunan  (sira onemli degil ama ardisik olmali)
cd /opt/alphawise/godmode/execution && docker compose up -d --no-deps godmode-execution
cd /opt/alphawise/godmode-paper-trading-service && docker compose -f docker-compose.paper.yml up -d --no-deps godmode-paper-trading

# 4) DOGRULAMA  (asagidaki kabul testi)
```

**Kritik not:** `EXECUTE_ADMIN_KEY`'e **dokunulmaz**. O ayrı bir sırdır
(`2d0ecb38…`) ve emir yüzeyini korur; bu döndürmeyle ilgisi yoktur.

### Döndürme B — oanda (bağımsız, sıfır riskli)

Ölçüldü: **oanda'yı çağıran hiçbir kod yok.** 7 günlük logunda 9.989
istek var ve **tamamı** kendi healthcheck'inin `/health` çağrısı.
Dolayısıyla anahtarını kimse sunmuyor; değiştirmek hiçbir çağrıyı kırmaz.

```bash
cp /opt/alphawise/commercial/AlphaWise-Elite/oanda-service/.env \
   /opt/alphawise/yedekler/oanda.env.rot_$(date +%Y%m%d_%H%M%S)
# oanda-service/.env:14  ADMIN_KEY=<yeni, execution'dan FARKLI bir deger>
cd /opt/alphawise/commercial/AlphaWise-Elite && docker compose up -d --no-deps oanda
```

oanda kendi `env_file: ./oanda-service/.env` dosyasını kullanıyor; Elite'in
ana `.env`'inde `ADMIN_KEY` **yok** (0 satır), yani başka servisi etkilemez.

---

## Kabul testi

Döndürme sonrası şunlar doğrulanmalı — **her biri ölçülebilir**:

```bash
# 1) Uc servisin sha256'lari ARTIK AYNI OLMAMALI
for c in alphawise-godmode-execution godmode-paper-trading alphawise-oanda; do
  docker inspect $c --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -E "^(ADMIN_KEY|GODMODE_ADMIN_KEY)=" \
  | while IFS='=' read -r k v; do
      echo "$c $k $(printf '%s' "$v" | sha256sum | cut -c1-16)"
    done
done
# BEKLENEN: execution ve paper-trading AYNI (cift), oanda FARKLI,
#           ucu de eski 7e02b48a6b016f45 degerinden FARKLI.

# 2) Okuma yolu calisiyor mu (paper-trading -> execution)
docker exec godmode-paper-trading python3 -c "
import os,asyncio,sys; sys.path.insert(0,'/app')
from src import karar
print(asyncio.run(karar.godmode_degerlendirmesi(
    os.getenv('GODMODE_URL'), os.getenv('GODMODE_ADMIN_KEY'), 'AAPL'))is not None)"

# 3) Emir yuzeyi ayrimi BOZULMADI mi (EXECUTE anahtari hala tek gecerli)
#    okuma anahtariyla emir ucu -> 401 beklenir
```

**Zamanlama:** piyasa kapalıyken yapılması önerilir — o zaman emir ucu
doğrulaması `BLOCKED_MARKET_CLOSED` döner ve emir riski sıfırdır.

---

## Geri alma

Her iki döndürme için de: yedek `.env` geri kopyalanır, ilgili konteyner
`--no-deps` ile yeniden kurulur. Kod değişmediği için `git revert`
gerekmez. Döndürme A'da **iki** dosya birlikte geri alınmalıdır.

---

## Sıfır pencere isteniyorsa (opsiyonel, kod değişikliği)

Ölçülen trafik sıfır olduğu için gerekli görülmedi. Gerekirse:
`godmode-execution`'a geçici bir `ADMIN_KEY_ESKI` desteği eklenir
(doğrulayıcı eski VEYA yeni değeri kabul eder), sunan taraf güncellenir,
sonra eski değer kaldırılır. Üç adımlı, penceresiz ama üç dağıtım
gerektirir.

---

## Bu plan neyi KAPSAMIYOR

- `PAPER_ADMIN_KEY` (`e83d83c7…`) ve `IZLENEN_LISTE_ANAHTARI` (`44e2fee2…`)
  — bunlar zaten ayrı ve paylaşılmıyor.
- `EXECUTE_ADMIN_KEY` (`2d0ecb38…`) — R-16'da üretildi, tek yerde.
- Alpaca anahtarları — R-15'in konusu, ayrı plan.
