# Tailscale ACL — AlphaWise-Elite

Bu dosya, EC2 sunucuları arasındaki ağ trafiğini **sıfır güven (zero-trust)**
prensibiyle sınırlar. Varsayılan **DENY**; sadece açıkça izin verilen trafik geçer.

## Mimarî

```
     ┌──────────────────┐               ┌──────────────────┐
     │  alphawise-2-app │  ──5432───▶   │  alphawise-1-db  │
     │  (tag:app)       │  ──6379───▶   │  (tag:db)        │
     │                  │  ──8000───▶   │                  │
     └──────────────────┘               └──────────────────┘
                       ▲                        ▲
                       │ SSH (tailscale ssh)    │
                       └────────┬───────────────┘
                                │
                          autogroup:admin  (sen)
```

## Kurulum Adımları

### 1) Auth key oluştur (Tailscale admin panelinden)
- https://login.tailscale.com/admin/settings/keys
- **Reusable** + **Ephemeral: OFF** + **Tags: tag:db** (db sunucusu için)
- Aynı işlemi `tag:app` için de tekrar et.

### 2) EC2 #1 (DB) sunucusunda:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up \
  --authkey=tskey-auth-XXXXXX \
  --advertise-tags=tag:db \
  --hostname=alphawise-1-db \
  --ssh
```

### 3) EC2 #2 (App) sunucusunda:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up \
  --authkey=tskey-auth-YYYYYY \
  --advertise-tags=tag:app \
  --hostname=alphawise-2-app \
  --ssh
```

### 4) ACL'i uygula:
- https://login.tailscale.com/admin/acls
- `tailscale.acl` içeriğini yapıştır → **Preview** → **Save**
- Preview sayfasında `tests` bloğunun tamamı yeşil olmalı.

## Doğrulama (EC2 #2 üzerinden)

```bash
# İzinli — çalışmalı
nc -zv alphawise-1-db 5432
nc -zv alphawise-1-db 6379
nc -zv alphawise-1-db 8000

# Yasak — bağlantı kurulamamalı (timeout / connection refused)
nc -zv alphawise-1-db 22       # SSH: sadece admin'e açık
nc -zv alphawise-1-db 9999     # keyfi port
```

## AWS Security Group ile Birlikte Kullanım

Tailscale ACL **uygulama katmanı** filtresidir. Ek güvenlik için AWS SG'de
şu kuralları da uygula:

**EC2 #1 (alphawise-1-db) SG:**
- Inbound 22/tcp     -> `0.0.0.0/0` KAPALI (Tailscale SSH kullan)
- Inbound 5432/tcp   -> sadece EC2 #2'nin private IP'sine izin ver
                       (VPC içi backup path — Tailscale down olursa)
- Inbound 6379/tcp   -> aynı
- Inbound 8000/tcp   -> aynı
- Inbound ALL        -> `100.64.0.0/10` (Tailscale CGNAT range) — opsiyonel

**EC2 #2 (alphawise-2-app) SG:**
- Inbound 22/tcp     -> `0.0.0.0/0` KAPALI
- Inbound 80/443     -> `0.0.0.0/0` (public web servisi ise)

## Sonraki Adımlar (Backlog)

- Yeni tag'ler: `tag:worker`, `tag:monitoring` (Prometheus/Grafana geldiğinde)
- Grafana -> tüm servislere okunur port erişimi (9090, 9187 exporter'lar)
- CI/CD runner için ayrı `tag:ci` tag'i (deployment sırasında)
