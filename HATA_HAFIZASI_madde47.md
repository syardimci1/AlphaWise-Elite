# HATA HAFIZASI — Madde 47 (SADECE EK)

### [2026-09-13 ~saat] Hata #1
Ne: `decision_log` tablosunda BEKLE kararları arasında tam bir yinelenen
satır var (`NVDA, 2026-08-02, pct_change=0.1356` iki kez, farklı `id`,
`evaluated_at` bir saat arayla).
Neden: Kök neden araştırılmadı (bu görevin kapsamı dışında — yalnızca
gözlem/ölçüm için okuma yapıldı, `decision_log`'a yazma yetkisi/görevi yok).
Muhtemel neden: değerlendirme işi (evaluate-decisions) aynı kararı iki kez
işlemiş olabilir.
Ders: Küçük örneklemli (n<20) canlı tablolardan istatistik çıkarırken tam
yinelenen satır kontrolü ZORUNLU olmalı — n=12 gibi küçük bir örnekte tek
bir yinelenen satır oranı %8 değiştirebilir.
Önlem: Bu görevde etkisi ölçüldü (12→11 benzersiz, sonuç zaten yetersiz
örnek olduğu için karara etkisi yok) ve raporlandı. Kalıcı düzeltme
(neden yinelendiği) bu görevin kapsamı dışında; ayrı bir madde olarak
kullanıcıya bildirilecek.
