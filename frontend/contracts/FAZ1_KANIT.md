# FAZ 1 — Doğrulama: Kanıt Dosyası

## 0.4 Çakışma kontrolü
```
git status --porcelain | grep -E "(chart|overlay|marker|route)"
```
Çıktı: BOŞ (exit 1) — çakışma yok, FAZ 1 başlatıldı.

## 1) Grafik bileşeni
- Dosya: `frontend/components/PriceChart.tsx`
- Kütüphane: `lightweight-charts` **v5.0.0** (`package.json`) — npm kurulum
  sırasında **"pre-release candidate version"** uyarısı veriyor, henüz
  stabil sürüm değil (bu bir VARSAYIM değil, `npm install` çıktısında
  görülen gerçek).
- Kullanım durumu: **hiçbir sayfada import edilmiyor**, git'te
  `??` (untracked) — canlı dashboard'da şu an çalışan bir fiyat grafiği
  YOK.

## 2) Marker/annotation API'si — CANLI test (sahte olayla uçtan uca)

Gerçek kurulu paket (`lightweight-charts@5.0.0`, standalone build)
izole bir `.html` sayfasında Playwright/Chromium ile çalıştırıldı
(kod yazılmadı diyen önceki fizibilite turunun aksine, bu fazda master
prompt "canlı dene" dediği için gerçek bir tarayıcıda ÇALIŞTIRILDI):

```js
const sahteOlay = { time: '2026-09-03', position: 'aboveBar',
  color: '#e63946', shape: 'arrowDown', text: 'INSIDER' };
const markerApi = LightweightCharts.createSeriesMarkers(series, [sahteOlay]);
```

**Sonuç (JS durumu, hatasız):**
```json
{
  "markerApiVarMi": true,
  "mevcutMarkerlar": [{"time":"2026-09-03","position":"aboveBar",
    "color":"#e63946","shape":"arrowDown","text":"INSIDER"}],
  "errors": []
}
```

**Ekran görüntüsü:** `contracts/kanit/faz1_marker_canli_kanit.png` —
kırmızı "INSIDER" ok işareti, 3 Eylül mumunun TAM ÜZERİNDE, doğru
konumda görsel olarak doğrulandı.

**Şüphecilik cevabı — "gerçekten annotation destekliyor mu, yoksa
sadece ok mu?":** İKİSİ BİRDEN. Aynı marker nesnesi hem `shape`
(ok/daire/kare) HEM `text` (kısa etiket) taşıyor ve ikisi de aynı anda
render edildi (ekran görüntüsünde "INSIDER" yazısı okun ÜZERİNDE
görünüyor). Zengin tooltip (hover'da detay kutusu) YERLEŞİK DEĞİL —
bu ayrı bir sınırlama olarak C2/FAZ2'ye taşındı.

## 3) 4 kaynağın uç doğrulaması
→ `contracts/kaynak_haritasi.md` (örnek istek+yanıt+C1 alan eşlemesi,
4 kaynağın hepsi için canlı, üretim konteynerlerinden).

**Bu fazda kendi kendine bulunan hata:** dark pool için önceki
değerlendirme eksikti — bkz. `HATA_HAFIZASI_koyfin.md` H-001.
`/regsho/{ticker}` (günlük, FINRA CDN, ücretsiz) keşfedildi.

## Çıkış kararı

PASS. Marker API canlı çalışıyor (ekran görüntüsü kanıtlı), 4 kaynağın
hepsi alan-eşlemesiyle C1'e bağlandı, çelişkili varsayım (V-002) aynı
fazda çözüldü. **FAZ 2'ye geçiliyor** (Otonom Karar Matrisi: test
PASS ∧ Y1-Y5 sağlam ∧ canlı yol teması yok — OTOMATİK İLERLE).
