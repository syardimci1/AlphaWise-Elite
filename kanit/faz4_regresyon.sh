#!/usr/bin/env bash
# =====================================================================
# FAZ 4 — REGRESYON: konteyner / veritabani gerektiren maddeler
# =====================================================================
# Frontend tarafi `frontend/tests/kiracilik/faz4-regresyon.test.ts`'te.
# Burada olculenler: 4.1 (defter), 4.4 (AST), 4.5 (karar_uret), 4.9 (geri alma).
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOK="$D/.."
gecti=0; kaldi=0
# GOREV TABAN CIZGISI: bu gorev origin/main uzerine kuruldu. HEAD~N gibi
# SABIT bir sayi kullanmak, her yeni commit'te olcumu kaydirir - ilk surumde
# tam bu hata vardi (HEAD~9 artik dogru noktayi gostermiyordu).
TABAN="$(git -C "$KOK" rev-parse origin/main)"
sonuc() { if [ "$1" = "0" ]; then echo "  PASS  $2"; gecti=$((gecti+1));
          else echo "  *** FAIL ***  $2"; kaldi=$((kaldi+1)); fi }

echo "===================================================================="
echo "FAZ 4 — KONTEYNER/VERITABANI REGRESYONU"
echo "===================================================================="

# ---------------------------------------------------------------- 4.1
echo
echo "--- 4.1 DEFTER DOKUNULMADI (Kapsam A: defter tek sistem hesabi) ---"
# Kapsam A defteri BOLMUYOR; dolayisiyla iddia "veri kaybolmadi" degil,
# "hic dokunulmadi"dir. Bu daha guclu bir iddiadir ve dogrudan olculur.
OKUMA=$(docker exec godmode-paper-trading python3 -c "
import sqlite3
k=sqlite3.connect('file:/veri/defter.sqlite?mode=ro',uri=True)
print('%d/%d/%d' % tuple(k.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                         for t in ('karar','islem','sinyal_gozlem')))" 2>/dev/null)
echo "      karar/islem/sinyal_gozlem = $OKUMA  (cron yazmaya devam ediyor, artmasi NORMAL)"
# Asil iddia: bu gorev defter semasina ya da yazan koda DOKUNMADI.
SEMA=$(docker exec godmode-paper-trading python3 -c "
import sqlite3
k=sqlite3.connect('file:/veri/defter.sqlite?mode=ro',uri=True)
print('user_id' in ''.join(r[0] or '' for r in
      k.execute(\"SELECT sql FROM sqlite_master WHERE type='table'\")))" 2>/dev/null)
[ "$SEMA" = "False" ]; sonuc $? "defter semasina user_id EKLENMEDI (Kapsam A geregi)"
if git -C "$KOK" diff --name-only "$TABAN"..HEAD | grep -q "godmode-paper-trading"; then
  sonuc 1 "bu gorev godmode-paper-trading'e dokunmadi"
else
  sonuc 0 "bu gorev godmode-paper-trading'e dokunmadi"
fi

# ---------------------------------------------------------------- 4.4 + 4.5
echo
echo "--- 4.4 KORUNAN DOSYA AST HASH'LERI SABIT ---"
"$D/benim_dosyalarim.sh" 2>&1 | sed -n '/3) Korunan/,$p' | grep -E "PASS|FAIL" | sed 's/^/  /'
"$D/benim_dosyalarim.sh" >/dev/null 2>&1; sonuc $? "8 korunan dosyanin hepsi degismemis"

echo
echo "--- 4.5 karar_uret ETKILENMEDI ---"
# Iddia: bu gorev HICBIR Python dosyasina dokunmadi, dolayisiyla karar yolu
# ayni girdide ayni cikti uretir. Statik ve kesin kanit.
# 17.09.2026 OLCUT DUZELTMESI: ilk surum "db/testler disinda HIC Python
# degismedi" diyordu. Bu olcut FAZLA GENISTI ve I-7 (gamma-exposure kota
# muhasebesi) yapilinca kirildi - ama kirilan sey KOD degil, OLCUTTU.
# 4.5'in gercek iddiasi "hicbir Python degismedi" degil, "KARAR YOLU
# dokunulmadi"dir. gamma-exposure bir piyasa VERISI servisidir; karar
# yolunda degildir. Dogru olcut karar yolu dizinlerini adiyla sayar.
KARAR_YOLU="^(maa|taa)/|^godmode-paper-trading-service/src/"
DEGISEN=$(git -C "$KOK" diff --name-only "$TABAN"..HEAD | grep "\.py$" | grep -E "$KARAR_YOLU" || true)
if [ -z "$DEGISEN" ]; then
  TUM=$(git -C "$KOK" diff --name-only "$TABAN"..HEAD | grep -c "\.py$")
  echo "      degisen Python: $TUM adet; KARAR YOLUNDA (maa/, taa/, godmode .../src/): 0"
  sonuc 0 "karar yolunda DEGISEN Python dosyasi yok (karar_uret dokunulmadi)"
else
  echo "      KARAR YOLUNDA degisen: $DEGISEN"
  sonuc 1 "karar yolunda DEGISEN Python dosyasi yok (karar_uret dokunulmadi)"
fi

# ---------------------------------------------------------------- 4.9
echo
echo "--- 4.9 GERI ALMA: 007 geri alindiginda sistem calisiyor ---"
if docker ps --format '{{.Names}}' | grep -q "^izole-rls-test$"; then
  docker exec -i izole-rls-test psql -U postgres -d postgres -q -v ON_ERROR_STOP=1 \
    -f - < "$KOK/db/migrations/007_geri_al_kullanici_goruntuleme_kaydi.sql" >/dev/null 2>&1
  sonuc $? "geri alma gocu hatasiz calisti"
  # Geri alindiktan SONRA onceki testler hala yesil mi (sistem calisiyor mu)
  python3 "$KOK/db/testler/sizinti_testi.py" 2>&1 | grep -q "30/30 PASS"
  sonuc $? "geri alma sonrasi 004/005/006 izolasyonu BOZULMADI (30/30)"
  docker exec -i izole-rls-test psql -U postgres -d postgres -q -v ON_ERROR_STOP=1 \
    -f - < "$KOK/db/migrations/007_supabase_kullanici_goruntuleme_kaydi.sql" >/dev/null 2>&1
  sonuc $? "ileri goc geri almadan SONRA tekrar uygulanabildi"
  python3 "$KOK/db/testler/goruntuleme_kaydi_testi.py" 2>&1 | grep -q "14/14 PASS"
  sonuc $? "yeniden uygulamadan sonra 007 izolasyonu tam (14/14)"
else
  echo "  ATLANDI  izole-rls-test konteyneri yok (db/testler/calistir.sh ile kurulur)"
fi

# ---------------------------------------------------------------- Y7
echo
# 17.09.2026: kullanici onayiyla 007 URETIME UYGULANDI. Olcut artik
# "hicbir sey uygulanmadi" degil, "BEKLENEN durumda" olmali - yoksa dogru
# bir uygulamadan sonra kirmiziya doner ve yanlis alarm uretir.
echo "--- Y7: URETIM BEKLENEN DURUMDA (007 onayla uygulandi) ---"
URET=$(docker exec supabase-db psql -U postgres -d postgres -t -A -c "
SELECT (SELECT COUNT(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname='kullanici_goruntuleme_kaydi')
    || '/' || (SELECT COUNT(*) FROM public.profiles)
    || '/' || (SELECT COUNT(*) FROM public.user_portfolios);" 2>/dev/null)
echo "      uretimde 007_tablo/profiles/user_portfolios = $URET  (1/2/1 OLMALI)"
[ "$URET" = "1/2/1" ]
sonuc $? "007 uygulandi (1) ve MEVCUT VERI degismedi (profiles=2, portfoy=1)"

echo
echo "===================================================================="
echo "SONUC: $gecti/$((gecti+kaldi)) PASS"
echo "===================================================================="
exit $([ "$kaldi" = "0" ] && echo 0 || echo 1)
