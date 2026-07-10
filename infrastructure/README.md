# AlphaWise-Elite Infrastructure

EC2 #1 (`alphawise-1-db`, Tailscale) veri katmanı.

## Kurulum (EC2 üzerinde)

```bash
# 1) Repoyu klonla ve dizine gir
git clone <repo-url> alphawise-elite && cd alphawise-elite

# 2) .env oluştur ve doldur
cp .env.example .env && vi .env

# 3) Servisleri başlat
docker compose up -d

# 4) Sağlık kontrolü
docker compose ps
docker compose logs -f --tail=50
```

## Alembic Migration

```bash
cd infrastructure
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# İlk şemayı uygula
alembic upgrade head
```

## Notlar

- **t2/t3.micro (1 GB RAM)** için tuning yapılmıştır (PG shared_buffers=128MB, Redis maxmemory=128mb).
- **Redis DB ayrımı** (CONSTITUTION Madde 16.3):
  - DB0 = cache
  - DB1 = rate-limit
  - DB2 = task-queue
  - DB3 = pub/sub
- **audit_log** tablosu WORM (Madde 12.3): UPDATE/DELETE trigger ile engellenir; ayrıca `audit_log` bir TimescaleDB **hypertable**'dır (7 günlük chunk).
- Fiyat/makro veri tabloları ileriki migration'larda eklendiğinde `create_hypertable('...','ts')` çağrısı ile aktifleştirilecek.
