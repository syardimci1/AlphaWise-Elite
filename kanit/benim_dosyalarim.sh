#!/usr/bin/env bash
# Y10/C8 — "bu gorev yalnizca kendi dosyalarina dokundu" iddiasini OLCER.
#
# Yontem: Faz 0'da alinan taban cizgisi (baskasinin commit edilmemis isi)
# bugunku git status'tan DUSULUR. Geriye kalan, bu gorevin urettigi kumedir.
# Ayrica cakisan 5 dosyanin icerik hash'i dogrulanir - "dokunmadim" iddiasi
# dosyanin git status'ta gorunup gorunmemesiyle degil, ICERIGIYLE kanitlanir.
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$D/.."

echo "=== 1) Bu gorevin dosyalari (taban cizgisi dusuldukten sonra) ==="
comm -13 "$D/faz0_baskasinin_isi_taban.txt" <(git status --porcelain | sort) | sed 's/^/  /'

echo
echo "=== 2) Cakisan dosyalar DEGISTI mi (hash dogrulamasi) ==="
if sha256sum -c "$D/faz0_cakisan_dosya_hashleri.txt" --quiet 2>/dev/null; then
  echo "  PASS  bes cakisan dosyanin da icerigi Faz 0'daki gibi - DOKUNULMADI"
else
  echo "  *** FAIL *** cakisan dosyalardan biri DEGISMIS:"
  sha256sum -c "$D/faz0_cakisan_dosya_hashleri.txt" 2>&1 | grep -v ": OK$" | sed 's/^/    /'
fi

echo
echo "=== 2b) Taban cizgisindeki dosyalar hala DURUYOR mu ==="
# 16.09.2026'DA OGRENILEN DERS: bolum 2 yalnizca BES cakisan dosyayi hash'liyordu.
# Taban cizgisindeki diger 49 girdiden birinin SILINMESI fark edilmiyordu - ve
# gercekten oldu: frontend/package-lock.json (baskasinin izlenmeyen dosyasi)
# bir temizlik sirasinda silindi ve bu betik "PASS" demeye devam etti.
# Artik taban cizgisindeki her IZLENMEYEN (??) dosyanin varligi dogrulaniyor.
eksik=0
while read -r durum yolu; do
  [ "$durum" = "??" ] || continue
  # Dizin girdileri (sonu / ile biten) icin dizin varligina bakilir.
  if [ ! -e "$yolu" ]; then
    echo "  *** EKSIK *** $yolu  (taban cizgisinde vardi, artik YOK)"
    eksik=$((eksik+1))
  fi
done < <(sed 's/^ *//' "$D/faz0_baskasinin_isi_taban.txt")
[ "$eksik" = "0" ] && echo "  PASS  taban cizgisindeki izlenmeyen dosyalarin hepsi yerinde"

echo
echo "=== 3) Korunan dosyalar (SHA-256 + AST) ==="
python3 - "$D/faz0_korunan_hashler.json" <<'PY'
import ast, hashlib, json, sys
from pathlib import Path
def ast_hash(m):
    t = ast.parse(m)
    for d in ast.walk(t):
        if isinstance(d,(ast.Module,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            b=d.body
            if b and isinstance(b[0],ast.Expr) and isinstance(b[0].value,ast.Constant) \
               and isinstance(b[0].value.value,str): d.body=b[1:] or [ast.Pass()]
    return hashlib.sha256(ast.dump(t,annotate_fields=True,include_attributes=False).encode()).hexdigest()
bekl=json.load(open(sys.argv[1])); hata=0
for yol,v in bekl.items():
    ham=Path(yol).read_bytes(); m=ham.decode('utf-8')
    s=hashlib.sha256(ham).hexdigest(); a=ast_hash(m)
    ok = (s==v['sha256'] and a==v['ast_sha256'])
    hata += (not ok)
    kisa=yol.split('/opt/alphawise/')[1]
    print(f"  {'PASS' if ok else '*** FAIL ***'}  [{v['kural']:9s}] {kisa}"
          + ("" if ok else f"\n        sha {v['sha256'][:12]} -> {s[:12]}\n        ast {v['ast_sha256'][:12]} -> {a[:12]}"))
sys.exit(1 if hata else 0)
PY
