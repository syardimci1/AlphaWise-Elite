#!/usr/bin/env bash
# =============================================================================
# R-15 / SECENEK B2 — GECIS ON KOSULU DEDEKTORU
# =============================================================================
#
# Kullanici B2'yi secti: paper-trading yeni bir Alpaca paper hesabina
# TASINIR, ama bu ancak DEFTER DUZ iken yapilabilir.
#
# NEDEN (olculdu): yeni hesapta pozisyon yoktur. Defter MSFT 20 iddia
# ederken gecilirse
#       fark = defter(20) - broker(0) = 20 > 0
#       -> emir_engelli = True
#       -> "DEFTER FAZLA IDDIA EDIYOR (hayalet pozisyon). Emir gonderilmez."
# Servis emir gonderemez hale gelir. Bu bir ariza degil, o kapinin isi -
# ama gecis o durumda yapilmamalidir.
#
# BU BETIK KARAR VERMEZ, OLCER. Hicbir sey degistirmez, emir gondermez;
# yalnizca okur.
#
# CIKIS KODU
#   0 = HAZIR      defter duz, mutabakat saglikli -> gecis yapilabilir
#   1 = HAZIR DEGIL defterde acik pozisyon var
#   2 = OLCULEMEDI  servise ulasilamadi / broker okunamadi (ariza-guvenli)
#
# Kullanim:  bash kanit/r15_gecis_hazir_mi.sh
# Donuk izleme:  watch -n 300 'bash kanit/r15_gecis_hazir_mi.sh; echo "kod=$?"'
# =============================================================================
set -uo pipefail

DEFTER=godmode-paper-trading

echo "R-15 / B2 GECIS ON KOSULU — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n' "------------------------------------------------------------"

CIKTI=$(docker exec "$DEFTER" python3 -c "
import os, json, urllib.request
h = {'x-admin-key': os.getenv('PAPER_ADMIN_KEY', '')}
try:
    d = json.load(urllib.request.urlopen(
        urllib.request.Request('http://127.0.0.1:8000/mutabakat', headers=h), timeout=30))
except Exception as e:
    print('OLCULEMEDI|' + type(e).__name__); raise SystemExit(0)

dp = d.get('defter_pozisyonlari') or {}
bp = d.get('broker_pozisyonlari') or {}
okundu = bool(d.get('okundu'))
engelli = bool(d.get('emir_engelli', False))
# Defterin YABANCI olmayan, kendi acik pozisyonlari
kendi = {s: q for s, q in dp.items() if abs(float(q)) > 1e-9}
print('|'.join([
    'OK',
    json.dumps(kendi, ensure_ascii=False),
    json.dumps(sorted(set(bp) - set(dp)), ensure_ascii=False),
    str(okundu), str(engelli), str(d.get('tutarli')),
]))
" 2>/dev/null)

if [ -z "$CIKTI" ] || [ "${CIKTI%%|*}" = "OLCULEMEDI" ]; then
  echo "  OLCULEMEDI: ${CIKTI#*|}"
  echo "  Ariza-guvenli: olculemeyen bir defter DUZ SAYILMAZ."
  exit 2
fi

IFS='|' read -r _ KENDI YABANCI OKUNDU ENGELLI TUTARLI <<< "$CIKTI"

printf '  %-28s %s\n' "defterin acik pozisyonu"  "$KENDI"
printf '  %-28s %s\n' "brokerdaki yabanci"       "$YABANCI"
printf '  %-28s %s\n' "broker okundu"            "$OKUNDU"
printf '  %-28s %s\n' "mutabakat tutarli"        "$TUTARLI"
printf '  %-28s %s\n' "emir engelli"             "$ENGELLI"
printf '%s\n' "------------------------------------------------------------"

if [ "$OKUNDU" != "True" ]; then
  echo "  SONUC: broker OKUNAMADI -> gecis yapilmaz (ariza-guvenli)."
  exit 2
fi

if [ "$KENDI" != "{}" ]; then
  echo "  SONUC: HAZIR DEGIL — defterde acik pozisyon var."
  echo "         B2 geregi bu pozisyon(lar) DOGAL olarak kapanana kadar beklenir;"
  echo "         zorla kapatmak B1 yoludur ve ayrica onay gerektirir."
  exit 1
fi

if [ "$ENGELLI" = "True" ]; then
  echo "  SONUC: HAZIR DEGIL — defter bos ama emir kapisi engelli;"
  echo "         once bu durumun nedeni giderilmeli."
  exit 1
fi

echo "  SONUC: HAZIR — defter duz, mutabakat saglikli."
echo "         Ikinci hesabin anahtarlari elde ise gecis yapilabilir:"
echo "         bkz. kanit/R15_AYRI_HESAP_PLANI.md, 'Uygulama adimlari'."
exit 0
