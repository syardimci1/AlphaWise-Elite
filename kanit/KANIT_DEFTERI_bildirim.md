# KANIT_DEFTERI — Bildirim Merkezi denetimi

| İddia | Kanıt yolu / komut | Zaman damgası |
|---|---|---|
| Bildirim merkezi zaten üretimde | `git log --oneline -- '*bildirim*'` → `08d5d60`…`b12b3d8` | 2026-09-26 |
| Okundu/okunmadı kalıcılığı yoktu | `grep -n "okundu\|unread" BildirimMerkezi.tsx` → yalnızca kaynak durumu eşleşmesi | 2026-09-26 |
| Otomatik yenileme yoktu | `grep -n "setInterval" BildirimMerkezi.tsx` → 0 eşleşme (değişiklik öncesi) | 2026-09-26 |
| Erişilebilirlik sıfırdı | `grep -n "aria-\|onKeyDown\|tabIndex" BildirimMerkezi.tsx` → 0 eşleşme (değişiklik öncesi) | 2026-09-26 |
| Yeni pure-fonksiyon testleri geçiyor | `node --test tests/bildirim-okundu.test.mjs` → `pass 16 / fail 0` | 2026-09-26 |
| Tam paket regresyonsuz | `npm test` → `.mjs pass 130/130`, `.ts pass 369/369` | 2026-09-26 |
| tsc yeni hata üretmiyor | `npx tsc --noEmit` → değişen dosyalarda 0 hata (2 alakasız önceden var olan hata hariç) | 2026-09-26 |
| Korunan dosyalar değişmedi | `sha256sum` taban vs sonra `diff` → fark yok | 2026-09-26 |
| Canlı: gerçek girişle rozet doğru sayıyor | Playwright snapshot: "25 okunmamis onemli kayit" → tıklama sonrası "24" | 2026-09-26T17:28 |
| Canlı: localStorage anahtarı doğru ad alanında | `browser_evaluate` → `alphawise:bildirim:okundu:v1:d7e28a7c-...` | 2026-09-26T17:28 |
| Canlı: klavye (Tab+Enter) okundu işaretliyor | `document.activeElement.getAttribute('aria-label')` önce/sonra | 2026-09-26T17:28 |
| Canlı: Escape paneli kapatıyor | `aria-expanded` kalkması, snapshot | 2026-09-26T17:28 |
| Canlı: gerçek iki-sekme senkronizasyonu | Sekme 2'de işaretleme → Sekme 0'da reload'suz rozet 23→22 | 2026-09-26T17:29 |
| Canlı: mobilde taşma yok | `browser_evaluate` `body.scrollWidth===innerWidth` @390px, `faz4_mobil_390px.png` | 2026-09-26T17:29 |
| Canlı: konsol/ağ temiz | `browser_console_messages`→0, `browser_network_requests`→5×200 | 2026-09-26T17:28-29 |
| Mutasyon testleri gerçekten çalıştırıldı | `sed` ile 3 mutasyon + `node --test` + `diff` ile geri dönüş doğrulaması | 2026-09-26 |
