# VARSAYIM DEFTERİ — karşılaştırma modu (grafik terminali)

Y14: soru sorulmadı; belirsizlikte muhafazakâr seçenek seçildi ve buraya yazıldı.

| # | Belirsizlik | Seçilen | Neden muhafazakâr |
|---|---|---|---|
| V-1 | İstemdeki `PriceChart.tsx` mi, terminal mi? | `GrafikTerminali.tsx` | PriceChart dashboard'daki eski grafik + olay katmanı; ona dokunmak başka bir özelliğin sözleşmesini değiştirirdi. "Grafik terminali" terminal bileşenidir. |
| V-2 | "2-3 sembol" ana sembolü sayar mı? | Sayar: ana + en fazla 2 ek = 3 | Daha küçük üst sınır; renk doğrulaması 3'te geçiyor. |
| V-3 | 4. sembol | Reddet + neden (otomatik çıkarma yok) | Kullanıcı verisi habersiz değişmez. |
| V-4 | Eksik gün: boşluk mu, LOCF mi? | Boşluk (saydam segment) | Değer uydurulmaz. |
| V-5 | Farklı başlangıç tarihleri | Ortak taban günü, öncesi dışarıda + sayı | "Aynı nokta, farklı gün" yanıltıcıdır. |
| V-6 | Kapanış düzeltilmiş mi? | İddia edilmez, etiketlenir; >%40 günlük hareket işaretlenir | Kaynak karışık, doğrulanamadı (FAZ 1 §3.2). |
| V-7 | Karşılaştırmada haftalık/aylık | Yalnızca günlük | Kova tarihleri semboller arasında hizalanmayabilir (ADR-6). |
| V-8 | Mod kalıcı mı? | Evet (`mod` alanı), seçimle birlikte | Yenilemede kullanıcı bıraktığı yerde; "sıfırla" ile silinir. |
| V-9 | Ana sembol değişince liste | Her ana sembolün kendi listesi (ad alanı ana sembol) | ADR-5 "seçim sembole aittir" kararıyla tutarlı. |
| V-10 | Ek sembolün verisi çekilemezse | Görünür hata, o sembol çizimden çıkar ama listede kalır | Geçici ağ hatası kullanıcının seçimini silmemeli. |
| V-11 | Karşılaştırma modunda PNG | Yok (düğme gizli) | Yanlış grafiğin (gizli mum grafiği) PNG'sini indirmek yanıltırdı; ayrı PNG kapsam dışı. |
| V-12 | Tarih penceresi | Ek sembollerde de 1500 bar (terminal ile aynı); dönem seçici yok | Yeni kavram eklemeden tutarlılık; taban tarihi lejantta açıkça yazılı. |
