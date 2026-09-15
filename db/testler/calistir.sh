#!/usr/bin/env bash
# =====================================================================
# İZOLE RLS DOĞRULAMA ORTAMINI SIFIRDAN KUR VE TÜM TEST AĞINI ÇALIŞTIR
# =====================================================================
# Üretim veritabanına DOKUNMAZ. Tek istisna: ACL karşılaştırması için
# `supabase-db` üzerinde SALT OKUMA sorgusu çalıştırılır.
#
# Kullanım:  ./calistir.sh          (ortamı kurar + testleri çalıştırır)
#            ./calistir.sh --sadece-test   (ortam ayakta, yalnız testler)
# =====================================================================
set -euo pipefail
KAP=izole-rls-test
BURA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOC="$BURA/../migrations"

psql_calistir() { docker exec -i "$KAP" psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f - < "$1"; }

if [[ "${1:-}" != "--sadece-test" ]]; then
  echo "### 1/6  izole PostgreSQL 17 konteyneri"
  docker rm -f "$KAP" >/dev/null 2>&1 || true
  docker run -d --name "$KAP" -e POSTGRES_PASSWORD=izole postgres:17 >/dev/null
  until docker exec "$KAP" pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done

  echo "### 2/6  roller, auth şeması, auth.uid()/role()"
  psql_calistir "$BURA/00_izole_kurulum.sql"

  echo "### 3/6  şema göçleri 004 + 005"
  psql_calistir "$GOC/004_supabase_profiles_user_portfolios_sema.sql"
  psql_calistir "$GOC/005_supabase_profiles_insert_politikasi_ve_auth_tetigi.sql"

  echo "### 4/6  ÜRETİM ACL'İNE EŞİTLE  (H-1'in yapısal önlemi)"
  psql_calistir "$BURA/01_uretim_acl_esitle.sql"

  echo "### 5/6  sahte kullanıcılar (A, B ve yetim C)"
  psql_calistir "$BURA/02_test_verisi.sql"

  echo "### 6/6  006 göçünü uygula"
  psql_calistir "$GOC/006_supabase_rls_kapsamayan_yollari_kapat.sql"
fi

echo
echo "====================== TEST AĞI ======================"
hata=0
for t in sizinti_testi.py yollar_testi.py goc_testi.py geri_alma_testi.py; do
  printf '%-22s ' "$t"
  ozet="$(python3 "$BURA/$t" 2>&1 | grep -oE 'SONUC: [0-9]+/[0-9]+ PASS' | tail -1 || true)"
  if [[ -z "$ozet" ]]; then echo "*** ÇALIŞMADI ***"; hata=1
  else
    echo "$ozet"
    [[ "${ozet#SONUC: }" =~ ^([0-9]+)/([0-9]+) ]] && [[ "${BASH_REMATCH[1]}" != "${BASH_REMATCH[2]}" ]] && hata=1
  fi
done
printf '%-22s ' "bypass_testi.py"
b="$(python3 "$BURA/bypass_testi.py" 2>&1 | grep -cE '\*\*\* (BULGU|KRITIK|REGRESYON) \*\*\*' || true)"
echo "bulgu sayısı: $b"; [[ "$b" != "0" ]] && hata=1

echo "======================================================"
if [[ "$hata" == "0" ]]; then echo "TÜM TESTLER GEÇTİ"; else echo "*** BAŞARISIZ ***"; fi
exit "$hata"
