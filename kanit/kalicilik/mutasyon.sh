#!/bin/sh
# MUTASYON TESTİ — kalıcılık testleri gerçekten koruyor mu?
#
# Her mutasyon kaynak koda bilerek bir hata sokar, ilgili testleri koşar ve
# testlerin KALMASINI bekler. Testler geçerse mutasyon HAYATTA KALMIŞTIR, yani
# test o hatayı yakalamıyordur. Kaynak her mutasyondan sonra git ile geri alınır.
#
# Kullanım: sh kanit/kalicilik/mutasyon.sh   (depo kökünden)
# E2E mutasyonları (M4, M5) için E2E_KOS ortam değişkeni kanit/kalicilik/e2e/kos.mjs
# koşturan bir komut olmalı; verilmezse o mutasyonlar ATLANDI olarak yazılır.
set -u
KOK=$(pwd)
BIRIM="cd $KOK/frontend && node --import tsx --test tests/grafik/*.test.ts"
hayatta=0

mutasyon() {
  ad=$1; dosya=$2; eski=$3; yeni=$4; komut=$5
  if ! grep -qF -- "$eski" "$dosya"; then
    echo "HATA   $ad: mutasyon noktası bulunamadı ($dosya)"; hayatta=$((hayatta + 1)); return
  fi
  python3 - "$dosya" "$eski" "$yeni" <<'EOF'
import sys
p, a, b = sys.argv[1:4]
s = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
EOF
  if [ "$komut" = "ATLA" ]; then
    echo "ATLANDI $ad (E2E_KOS verilmedi)"
  elif sh -c "$komut" >/tmp/mutasyon_cikti.txt 2>&1; then
    echo "HAYATTA $ad  <-- testler hatayı YAKALAMADI"; hayatta=$((hayatta + 1))
  else
    ozet=$(grep -E "^# fail|^KALDI" /tmp/mutasyon_cikti.txt | head -3 | tr '\n' ' ')
    echo "ÖLDÜ   $ad  [$ozet]"
  fi
  git -C "$KOK" checkout -q -- "$dosya"
}

E2E=${E2E_KOS:-ATLA}
e2e() { if [ "$E2E" = "ATLA" ]; then echo ATLA; else echo "$E2E $1"; fi; }

mutasyon "M1 debounce kaldırıldı (planla hemen yazar)" \
  frontend/src/lib/grafik/gecikmeli-kayit.ts \
  "    this.iptal(anahtar)
    const tutamac" \
  "    this.iptal(anahtar)
    yaz(); return
    const tutamac" \
  "$BIRIM"

mutasyon "M2 şema sürüm kontrolü bozuldu (v yok sayılır)" \
  frontend/src/lib/grafik/gosterge-kalicilik.ts \
  "if (zarf.v !== SURUM) {" \
  "if (false) {" \
  "$BIRIM"

mutasyon "M3 ad alanı anahtarı sabitlendi (kimlik yok sayılır)" \
  frontend/src/lib/grafik/cizim-kalicilik.ts \
  'return `${onek}:${parcaKacisla(kimlik)}:${parcaKacisla(normalSembol)}`' \
  'return `${onek}:sabit:${parcaKacisla(normalSembol)}`' \
  "$BIRIM"

mutasyon "M4 H-1 kapısı geri alındı (çizim kaydı yalnızca sembole bakar)" \
  frontend/components/GrafikTerminali.tsx \
  "    if (yuklenenCizimAnahtari !== anahtarUret(etkinKimlik, symbol)) return" \
  "    if (yuklenenCizimAnahtari === null || !yuklenenCizimAnahtari.endsWith(':' + symbol)) return" \
  "$(e2e E5b)"

mutasyon "M5 yankı kapısı kaldırıldı (yüklenen veri geri yazılır)" \
  frontend/components/GrafikTerminali.tsx \
  "    if (depodakiRef.current.get(anahtar) === icerik) return
    depodakiRef.current.set(anahtar, icerik)
    kayitci.planla(anahtar, () => {
      // B5" \
  "    depodakiRef.current.set(anahtar, icerik)
    kayitci.planla(anahtar, () => {
      // B5" \
  "$(e2e E11)"

mutasyon "M6 sıfırlamada bekleyen yazım iptali kaldırıldı" \
  frontend/src/lib/grafik/kalicilik-sifirlama.ts \
  "  kayitci.iptal(gostergeAnahtari(kullaniciKimligi, sembol))" \
  "" \
  "$BIRIM"

mutasyon "M7 pagehide/kaldırma boşaltması kaldırıldı" \
  frontend/src/lib/grafik/gecikmeli-kayit.ts \
  "    for (const { yaz } of isler) {" \
  "    for (const { yaz } of []) {" \
  "$BIRIM"

mutasyon "M8 kota tanıma bozuldu (her hata kota değil)" \
  frontend/src/lib/grafik/cizim-kalicilik.ts \
  "  if (!(hata instanceof Error)) return false" \
  "  return false" \
  "$BIRIM"

echo
echo "hayatta kalan / bulunamayan: $hayatta"
exit $hayatta
