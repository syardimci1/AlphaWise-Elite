# Qdrant Değerlendirmesi — ve Asıl Darboğazın Ölçümü

**Madde 48** — *Qdrant*
**Tarih:** 10 Eylül 2026

## Kısa sonuç

**Qdrant benimsenmedi.** Gerekçesi ölçüldü ve bulunamadı: sorgu süresinin
%97'si ChromaDB'nin işi *değil*. Ölçüm sırasında asıl darboğaz bulundu ve
düzeltildi — tekrar eden sorgular **38 kat** hızlandı.

## 1. Mevcut durum

İki ChromaDB örneği çalışıyor:

| örnek | koleksiyon | kayıt | disk |
|---|---|---:|---:|
| `alphawise-chromadb` | 4 (asıl: `alphawise_knowledge`) | 14.350 | 207 MB |
| `alphawise-hafiza-chromadb` | 1 | — | 24 MB |

14.350 vektör, vektör veritabanı ölçeğinde **küçüktür**. Qdrant'ın öne
çıktığı yerler (HNSW ayarı, parçalama, milyonlarca vektörde filtreleme)
bu ölçekte devreye girmez.

## 2. Ölçüm: süre nerede geçiyor?

`alphawise_knowledge` (14.329 kayıt), 20 sorgu:

| aşama | medyan | p95 | pay |
|---|---:|---:|---:|
| **Gömme** (sentence-transformers) | **521 ms** | 807 ms | **%97** |
| **Vektör arama** (ChromaDB) | **14 ms** | 22 ms | **%3** |

Sorgu süresinin neredeyse tamamı, sorgu **metnini vektöre çevirmekte**
geçiyor. Qdrant o %3'ü hedefler ve **gömmeyi o da yapmaz.**

> Bu, bu oturumda ikinci kez karşılaşılan yanlış atıf riskiydi (ilki
> vectorbt'nin numba derlemesini "darboğaz" sanmaktı). Ölçmeden bakıldığında
> "662 ms sorgu, vektör veritabanı yavaş" demek doğal görünüyor.

## 3. Asıl düzeltme: sorgu gömmesi önbelleği

Aynı metin her sorguda yeniden gömmeleniyordu. Süreç-içi, sınırlı boyutlu
(LRU, 512) bir önbellek eklendi.

**Neden Redis değil:** `rag` servisinde Redis ne ortam değişkeni ne de
bağımlılık olarak var. Tek süreçlik bir servis için süreç-içi önbellek aynı
kazancı bağımlılık eklemeden veriyor. Bedeli **açıkça bildiriliyor**:
önbellek yeniden başlatmada kaybolur ve kopyalar arasında paylaşılmaz.

**Model kimliği anahtarın parçasıdır.** Gömme modeli değişirse eski
vektörler sessizce yanlış sonuç üretirdi. Sürüm etiketine güvenmek yerine
model, sabit bir deneme metninin gömmesinden türetilen bir **parmak iziyle**
tanımlanıyor: model değişirse parmak izi kendiliğinden değişir ve önbellek
geçersizleşir. Kimsenin bir sürüm numarasını elle artırması gerekmez.

**Önce denklik doğrulandı.** İstemci tarafında gömme yapmak, sunucunun
indeksleme modeliyle aynı olmasını gerektirir; farklıysa arama sonuçları
sessizce bozulur. Beş sorguda `query_texts` (sunucu gömer) ile
`query_embeddings` (istemci gömer) karşılaştırıldı: **beşinde de aynı
kimlikler ve aynı mesafeler** döndü.

**Önbellek bir hızlandırmadır, bağımlılık değil.** Çalışmazsa arama yine
yapılır (metin yoluna düşülür) — sessizce boş sonuç dönmek, "eşleşme yok" ile
"gömmelenemedi"yi aynı gösterirdi.

## 4. Canlı ölçüm

```
tekrar eden sorgu : 0,602 s  ->  0,016 s     (38 kat)
yeni sorgu        : 0,602 s  ->  0,510 s     (değişmedi, beklenen)
soğuk ilk sorgu   : 19,8 s   ->  1,17 s
```

Soğuk başlangıç düzeltmesi ayrı bir bulgudan geldi: model **çalışma anında**
indiriliyordu (`/root/.cache` 167 MB). Yani her konteyner yeniden
oluşturmada ~90 MB tekrar iniyor ve servis çalışma anında ağa bağımlı
oluyordu. Model artık **derleme aşamasında** indiriliyor.

Bedel: `rag` konteyneri 104 MiB bellek kullanıyor (model yüklü). Kabul
edilebilir — ana makinede 30 GB boş var.

## 5. Şüphecilik turu

| # | mutasyon | sonuç |
|---|---|---|
| M1 | anahtardan model parmak izini çıkar | YAKALANDI |
| M2 | kapasite sınırını uygulama (sınırsız büyüme) | YAKALANDI |
| M3 | isabette LRU sırasını güncelleme | YAKALANDI |
| M4 | hiç sorgu yokken isabet oranı 0 göster | YAKALANDI |
| M5 | metin türü denetimini kaldır | YAKALANDI |
| M6 | parmak izini sabitle (model değişikliği görünmez olur) | YAKALANDI |

**Hayatta kalan mutasyon yok (0/6).** 18 test.

## 6. Qdrant hangi durumda gerekli olurdu

- Vektör sayısı milyonlara çıkarsa (şu an 14.350)
- Karmaşık meta veri filtreleriyle arama gerekirse
- Yatay ölçekleme / parçalama gerekirse

Hiçbiri şu an geçerli değil. Ölçüm tekrarlanabilir; koşullar değişirse karar
da değişebilir.

## 7. Yan bulgu (düzeltilmedi)

`alphawise_knowledge` sorgularında ilk iki isabet **aynı dosya ve aynı
mesafe** dönüyor (`docs/ja/workflows.md`, uzaklık 1,4524) — indekste yinelenen
parçalar var. Bu mevcut bir durum, bu maddenin değişikliğinden kaynaklanmıyor
ve ayrı bir iş.

## 8. Üretilen dosyalar

- `rag/src/gomme_onbellek.py` — parmak izine bağlı LRU gömme önbelleği
- `rag/src/main.py` — `/query` ve `/query-sinyaller` önbelleğe bağlandı, `/gomme-onbellek` teşhis ucu
- `rag/Dockerfile` — model derleme aşamasında indiriliyor
- `rag/tests/test_gomme_onbellek.py` — 18 test
