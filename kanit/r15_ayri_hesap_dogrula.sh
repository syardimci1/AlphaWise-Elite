#!/usr/bin/env bash
# =============================================================================
# R-15 KABUL TESTI — iki emir yuzeyi AYRI broker hesabinda mi?
# =============================================================================
#
# NEDEN VAR (olculdu 20.09.2026): godmode/execution ile godmode-paper-trading
# AYNI Alpaca paper hesabini (PA30SBB6QS52) kullaniyordu. Pozisyon tarafi
# bilincli olarak ele alinmisti, ama zarar-durdurma esigi su bicimde kaliyordu:
#
#     pv  = istemci().hesap()["portfolio_value"]        <- PAYLASILAN hesap
#     risk.zarar_durumu_belirle(pv, defter...zarar)     <- YALNIZCA defter
#     -> abs(zarar) >= pv * 0.20 ise DURDURULMUS
#
# Payi bir kitaptan, paydayi baska bir kitabi da iceren hesaptan almak,
# durdurma esigini bu servisin kendi sermayesinin cok ustune tasiyordu.
#
# BU BETIK SIR YAZDIRMAZ. Anahtarlar yalnizca sha256 ozetiyle karsilastirilir;
# hesap numarasi Alpaca'nin kendi acik kimligidir (sir degildir).
#
# CIKIS KODU:  0 = AYRI hesaplar (R-15 kapali)   1 = AYNI hesap (R-15 acik)
#
# Kullanim:  bash kanit/r15_ayri_hesap_dogrula.sh
# =============================================================================
set -uo pipefail

YURUTME=alphawise-godmode-execution
DEFTER=godmode-paper-trading

ayir() { printf '%s\n' "------------------------------------------------------------"; }

echo "R-15 KABUL TESTI — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
ayir

# --- 1) Anahtar ozetleri --------------------------------------------------
YUR_OZET=$(docker exec "$YURUTME" python3 -c "
import os,hashlib
k=os.getenv('ALPACA_API_KEY','')
print(hashlib.sha256(k.encode()).hexdigest()[:16] if k else 'BOS')" 2>/dev/null)

DEF_OZET=$(docker exec "$DEFTER" python3 -c "
import os,hashlib
k=os.getenv('ALPACA_PAPER_API_KEY','')
print(hashlib.sha256(k.encode()).hexdigest()[:16] if k else 'BOS')" 2>/dev/null)

printf '  %-34s %s\n' "execution ALPACA_API_KEY" "${YUR_OZET:-OKUNAMADI}"
printf '  %-34s %s\n' "paper ALPACA_PAPER_API_KEY" "${DEF_OZET:-OKUNAMADI}"

if [ -z "${YUR_OZET:-}" ] || [ -z "${DEF_OZET:-}" ]; then
  echo "  HATA: anahtar ozetleri okunamadi (konteynerler ayakta mi?)"
  exit 2
fi

# --- 2) Canli hesap numaralari -------------------------------------------
ayir
YUR_HESAP=$(docker exec "$YURUTME" python3 -c "
import os
from alpaca.trading.client import TradingClient
c=TradingClient(os.getenv('ALPACA_API_KEY'),os.getenv('ALPACA_SECRET_KEY'),paper=True)
a=c.get_account(); print(f'{a.account_number}|{a.equity}')" 2>/dev/null)

DEF_HESAP=$(docker exec "$DEFTER" python3 -c "
import os,json,urllib.request
h={'x-admin-key':os.getenv('PAPER_ADMIN_KEY','')}
d=json.load(urllib.request.urlopen(
    urllib.request.Request('http://127.0.0.1:8000/hesap',headers=h),timeout=30))
print(f\"{d.get('hesap_numarasi') or '?'}|{d.get('portfoy_degeri') or '?'}\")" 2>/dev/null)

printf '  %-34s %s\n' "execution hesap|oz sermaye" "${YUR_HESAP:-OKUNAMADI}"
printf '  %-34s %s\n' "paper     hesap|oz sermaye" "${DEF_HESAP:-OKUNAMADI}"

# --- 3) Defterin bilmedigi sermaye ---------------------------------------
ayir
docker exec "$DEFTER" python3 -c "
import os,json,urllib.request
h={'x-admin-key':os.getenv('PAPER_ADMIN_KEY','')}
d=json.load(urllib.request.urlopen(
    urllib.request.Request('http://127.0.0.1:8000/mutabakat',headers=h),timeout=30))
dp=d.get('defter_pozisyonlari') or {}
bp=d.get('broker_pozisyonlari') or {}
yabanci=sorted(set(bp)-set(dp))
print(f'  defterin bildigi sembol : {sorted(dp)}')
print(f'  brokerdaki YABANCI      : {len(yabanci)} {yabanci}')
print(f'  mutabakat tutarli       : {d.get(\"tutarli\")}')
print(f'  emir engelli            : {d.get(\"emir_engelli\", False)}')
" 2>/dev/null

# --- 4) KARAR -------------------------------------------------------------
ayir
if [ "$YUR_OZET" = "$DEF_OZET" ]; then
  echo "  SONUC: AYNI ANAHTAR -> iki yuzey AYNI hesapta. R-15 ACIK."
  echo "         zarar_durumu_belirle paydasi baska bir kitabin sermayesini de iceriyor."
  exit 1
fi

if [ -n "${YUR_HESAP:-}" ] && [ -n "${DEF_HESAP:-}" ] \
   && [ "${YUR_HESAP%%|*}" = "${DEF_HESAP%%|*}" ]; then
  echo "  SONUC: anahtarlar farkli ama HESAP NUMARASI AYNI -> ayrim gercek degil."
  echo "         (ayni hesap icin ikinci bir anahtar cifti uretilmis olabilir)"
  exit 1
fi

echo "  SONUC: AYRI hesaplar. R-15 KAPALI."
echo "         Her yuzeyin zarar esigi artik kendi sermayesine dayaniyor."
exit 0
