#!/usr/bin/env bash
# ===========================================================================
# PORT YAYIN DENETIMI — ic servisler disariya acilmasin
#
# NEDEN VAR (23.08.2026):
# Denetimde MAA'nin (:8005) "disaridan kimliksiz erisilebilir" oldugu
# VARSAYILMISTI. Olculdu ve dogru cikmadi: tum konteyner portlari
# 127.0.0.1'e sabitli, disaridan erisim yok. Ancak bu koruma tek bir
# on eke bagli — docker-compose.yml'de "127.0.0.1:8005:8000" yerine
# "8005:8000" yazmak yeterli olurdu ve bu SESSIZ bir regresyon olurdu:
# hicbir test kirilmaz, servis calismaya devam eder, yalnizca internete
# acilir. Ustelik Docker port yayini ufw'yi ATLAR (DNAT, INPUT zincirinden
# once) — yani guvenlik duvari kurallari bu hatayi yakalamaz.
#
# Cikis kodu 0 = temiz, 1 = disariya acik yayin var.
# ===========================================================================
set -uo pipefail

echo "== Konteyner port yayinlari denetleniyor =="
ACIK=0

while IFS=$'\t' read -r ad portlar; do
    [ -z "$portlar" ] && continue
    if echo "$portlar" | grep -qE '(^|, )(0\.0\.0\.0|\[::\]):'; then
        echo "  ACIK: $ad -> $portlar"
        ACIK=$((ACIK + 1))
    fi
done < <(docker ps --format '{{.Names}}\t{{.Ports}}')

if [ "$ACIK" -gt 0 ]; then
    echo "SONUC: $ACIK konteyner TUM arayuzlere acik. Beklenen: hepsi 127.0.0.1."
    echo "Duzeltme: docker-compose.yml'de port satirini '127.0.0.1:<host>:<kap>' yapin."
    exit 1
fi
echo "  Tum yayinlar 127.0.0.1'e sabitli."

echo "== Dogrudan disaridan erisim denemesi =="
DIS_IP=$(ip -4 addr show scope global | grep -oP 'inet \K[\d.]+' | head -1)
if [ -n "$DIS_IP" ]; then
    for PORT in 8005 3000; do
        KOD=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://$DIS_IP:$PORT/" || true)
        if [ "$KOD" = "000" ]; then
            echo "  $DIS_IP:$PORT -> erisilemiyor (BEKLENEN)"
        else
            echo "  $DIS_IP:$PORT -> HTTP $KOD  (BEKLENMEYEN: disaridan erisilebiliyor)"
            ACIK=$((ACIK + 1))
        fi
    done
else
    echo "  Genel IP bulunamadi, bu adim atlandi."
fi

if [ "$ACIK" -eq 0 ]; then echo "SONUC: TEMIZ"; exit 0; else echo "SONUC: SORUNLU"; exit 1; fi
