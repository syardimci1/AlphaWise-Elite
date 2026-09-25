#!/bin/sh
# MUTASYON TESTİ — karşılaştırma testleri gerçekten koruyor mu?
#
# Her mutasyon kaynağa bilerek bir hata sokar, ilgili testleri koşar ve testlerin
# KALMASINI bekler. Testler geçerse mutasyon HAYATTA KALMIŞTIR (test o hatayı
# yakalamıyor). Kaynak her mutasyondan sonra git ile geri alınır — çalışma
# kopyası temiz olmalı.
#
# Kullanım (depo kökünden): sh kanit/karsilastirma/mutasyon.sh
# E2E mutasyonları için E2E_KOS, kanit/karsilastirma/e2e/kos.mjs koşturan bir komut
# olmalı (ör. "node kanit/karsilastirma/e2e/kos.mjs"); verilmezse ATLANDI yazılır.
set -u
KOK=$(pwd)
BIRIM="cd $KOK/frontend && node --import tsx --test tests/grafik/*.test.ts"
hayatta=0

mutasyon() {
  ad=$1; dosya=$2; eski=$3; yeni=$4; komut=$5
  if ! grep -qF -- "$eski" "$dosya"; then
    echo "HATA   $ad: mutasyon noktası bulunamadı ($dosya)"; hayatta=$((hayatta + 1)); return
  fi
  python3 - "$dosya" "$eski" "$yeni" <<'PY'
import sys
p, a, b = sys.argv[1:4]
s = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
PY
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
e2e() { if [ "$E2E" = "ATLA" ]; then echo ATLA; else echo "cd $KOK && $E2E $1"; fi; }
K=frontend/src/lib/grafik/karsilastirma.ts

mutasyon "M1 köprü segmenti saydam yapılmıyor (Y9 görsel enterpolasyon)" $K \
  "if (i < sonDoluIndeks && degerler[i + 1] === null) nokta.color = SAYDAM" \
  "void sonDoluIndeks" "$BIRIM"

mutasyon "M2 her seri KENDİ ilk gününe göre %0 (ortak taban yok)" $K \
  "const tabanKapanis = t.harita.get(tabanTarihi) as number" \
  "const tabanKapanis = t.harita.get(t.tarihler[0]) as number" "$BIRIM"

mutasyon "M3 eksik gün son bilinen değerle taşınıyor (LOCF)" $K \
  "        degerler.push(null)
        // Son bardan" \
  "        degerler.push(degerler.length > 0 ? degerler[degerler.length - 1] : null)
        // Son bardan" "$BIRIM"

mutasyon "M4 4. sembolde en eski otomatik çıkarılıyor" $K \
  "if (yuva === undefined) return { tamam: false, neden: 'dolu', metin: KARSILASTIRMA_METINLERI.dolu }" \
  "if (yuva === undefined) return { tamam: true, secim: { ...secim, semboller: [...secim.semboller.slice(1), { sembol, yuva: secim.semboller[0].yuva }] } }" "$BIRIM"

mutasyon "M5 yinelenen sembol denetimi kaldırıldı" $K \
  "if (secim.semboller.some((s) => s.sembol === sembol)) {" \
  "if (false) {" "$BIRIM"

mutasyon "M6 renk sıraya bağlı (çıkarınca yuvalar yeniden numaralanıyor)" $K \
  "return kalan.length === secim.semboller.length ? secim : { ...secim, semboller: kalan }" \
  "return kalan.length === secim.semboller.length ? secim : { ...secim, semboller: kalan.map((s, i) => ({ ...s, yuva: (i + 1) as 1 | 2 })) }" "$BIRIM"

mutasyon "M7 kalıcılık anahtarı kimliği yok sayıyor (hesaplar arası sızıntı)" frontend/src/lib/grafik/karsilastirma-kalicilik.ts \
  "return adAlaniAnahtari(ANAHTAR_ONEKI, kullaniciKimligi, anaSembol)" \
  "return adAlaniAnahtari(ANAHTAR_ONEKI, 'ortak', anaSembol)" "$BIRIM"

mutasyon "M8 sıfırlama karşılaştırma kaydını silmiyor" frontend/src/lib/grafik/kalicilik-sifirlama.ts \
  "    karsilastirmaSil(depo, kullaniciKimligi, sembol)," \
  "" "$BIRIM"

# M9 ilk koşuda K2'ye bağlıydı ve HAYATTA kaldı: H-6'nın ikinci düzeltmesinden sonra K2
# grafiği hiç kaldırmıyor. Kaldırma yolu mod geçişidir (K6; ayrıca K1/K13/K15 de öldürüyor).
mutasyon "M9 H-6 kapısı geri alındı (yok edilmiş grafikte removeSeries)" frontend/components/KarsilastirmaGrafigi.tsx \
  "if (grafikRef.current !== grafik) return" \
  "" "$(e2e K6)"

mutasyon "M10 karşılaştırma modunda Delete koruması kaldırıldı" frontend/components/GrafikTerminali.tsx \
  "    if (karsilastirmaModu) return
    const tus = (olay: KeyboardEvent): void => {" \
  "    const tus = (olay: KeyboardEvent): void => {" "$(e2e K10)"

mutasyon "M11 mum grafiği gizlenmek yerine kaldırılıyor (C6 görünüm kaybı)" frontend/components/GrafikTerminali.tsx \
  "style={{ marginTop: 10, display: gorunum.grafik === 'mum' ? 'block' : 'none' }}" \
  "style={{ marginTop: 10, display: gorunum.grafik === 'mum' ? 'block' : 'none' }} key={gorunum.grafik}" "$(e2e K6)"

echo
if [ $hayatta -eq 0 ]; then echo "SONUÇ: tüm mutasyonlar öldü"; else echo "SONUÇ: $hayatta mutasyon HAYATTA / hatalı"; fi
exit $hayatta
