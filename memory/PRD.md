# AlphaWise-Elite — PRD

## Problem Statement (özet)
AlphaWise-Elite kişisel yatırım/analiz platformu için altyapı kurulumu.
Bu iterasyon: **EC2 #1 (`alphawise-1-db`, Tailscale)** üzerinde çalışacak veri
katmanı — PostgreSQL+TimescaleDB, Redis 7, ChromaDB — ve Alembic migration'ları.

## Anayasa (CONSTITUTION.md) — bu iterasyonda uygulanan maddeler
- **Madde 3.4** — AgentOutput Pydantic şeması (birebir alanlar)
- **Madde 12.3** — Immutable Audit Trail (WORM): `audit_log` UPDATE/DELETE trigger'ı
- **Madde 13.1** — Mikroservis mimarisi (services/… ileri iterasyonlarda)
- **Madde 16.3** — Alembic + TimescaleDB hypertable + Redis 4 DB ayrımı + Chroma

## Mimari — bu iterasyon
```
EC2 #1  alphawise-1-db (Tailscale)
  ├── postgres  (timescale/timescaledb:2.17.2-pg16)  :5432
  ├── redis     (redis:7.4-alpine)                    :6379
  └── chroma    (chromadb/chroma:0.5.15)              :8000
```

## Implemented (2026-01-15)
- `docker-compose.yml` — 3 servis, 1 GB RAM tuning, healthcheck, log rotation
- `.env.example` — tüm env değişkenleri (POSTGRES_*, REDIS_*, CHROMA_*, DATABASE_URL)
- `infrastructure/requirements.txt` — alembic 1.14, SQLAlchemy 2.0.36, psycopg2-binary 2.9.10, pydantic 2.10.3 (versiyonlar pinlenmiş)
- `infrastructure/alembic.ini` + `alembic/env.py` + `script.py.mako`
- `infrastructure/alembic/versions/001_initial_schema.py`
  - Tablolar: `users`, `portfolios` (market=US|BIST), `reports`, `agent_decisions`, `audit_log`
  - `pgcrypto` + `timescaledb` extension
  - WORM trigger'lar (audit_log UPDATE/DELETE engelli)
  - `audit_log` → TimescaleDB hypertable (7 günlük chunk)
- `infrastructure/common/schemas/agent_output.py` (Madde 3.4 birebir)
- `infrastructure/common/schemas/handoff_request.py` (from alias'ı ile)
- `.gitignore`'a `.env` ve varyantları eklendi
- **`infrastructure/tailscale.acl`** — zero-trust ACL (tag:db, tag:app, tag:admin) + Tailscale SSH + ACL testleri
- **`infrastructure/tailscale.acl.README.md`** — kurulum + AWS SG entegrasyon rehberi

## Doğrulanan Testler
- `python -c` ile Pydantic şema instantiation ✓
- Alembic migration import + compile ✓
- docker-compose YAML parse ✓ (docker binary bu container'da yok — asıl `docker compose config` EC2'de çalıştırılacak)
- Lint (ruff) temiz ✓

## Bilinen Sınırlamalar / Notlar
- `docker compose config` bu preview container'ında çalıştırılamadı (docker binary yok). EC2'de `docker compose --env-file .env config` ile son doğrulama yapılmalı.
- CONSTITUTION.md dosyası henüz repoya eklenmedi (kullanıcı manuel yükleyecek).
- Fiyat/makro veri tabloları henüz yok — sadece TimescaleDB extension hazırlandı. `market_data`, `macro_indicators` tabloları sonraki migration'da eklenecek ve `create_hypertable` ile aktif edilecek.
- Qdrant failover, Neo4J ileri iterasyonlarda.

## Backlog (öncelik sırası)
- **P0** GitHub repo bağlantısı + Save to GitHub push
- **P0** EC2 #1'de `docker compose up -d` doğrulama + `alembic upgrade head`
- **P1** `market_data` (ticker, ts, ohlcv) & `macro_indicators` (series_id, ts, value) tabloları + hypertable
- **P1** services/ altındaki 18 mikroservis iskeletleri (Madde 13.1)
- **P2** ChromaDB → Qdrant failover
- **P2** Neo4J entegrasyonu
- **P2** WORM audit servisi (Kafka/NATS köprüsü)

## Sonraki Adım Kullanıcı için
1. `.env.example` → `.env` kopyala, gerçek değerleri gir
2. "Save to GitHub" ile push et
3. EC2 #1'e SSH ile bağlan, repoyu clone et, `docker compose up -d`
4. `cd infrastructure && pip install -r requirements.txt && alembic upgrade head`
