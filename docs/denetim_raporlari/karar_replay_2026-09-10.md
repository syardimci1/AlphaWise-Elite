# Karar Replay Denetimi — 10 Eylül 2026

**Madde 34** — *Karar replay yeteneği (decision_log'dan tam yeniden oynatma)*

## Soru

Sistem, geçmişte verdiği bir kararı bugün aynen yeniden üretebiliyor mu? Üretemiyorsa
"bu karar neden verildi" sorusunun yanıtı kayıttaki metne güvenmek zorunda kalır ve
kayıt ile kod arasındaki sessiz bir ayrışma hiç fark edilmez.

## Yöntem

`maa/src/karar_replay.py` karar kuralını **bağımsız olarak** uygular. Canlı kural
`maa/src/main.py` içindedir ve o dosya korunmuştur — hem değiştirilemez hem de ithal
edilemez (ithal etmek FastAPI, LLM istemcisi ve veritabanı bağlantılarını da
yüklerdi). Bu yüzden kural belgelendiği gibi yeniden yazıldı:

| koşul | karar |
|---|---|
| geçerli (None olmayan) katman < 3 | BEKLE, toplam skor üretilmez |
| toplam ≤ -3 | DİKKAT ET |
| toplam ≥ 4 | EKLE |
| aksi | TUT |

Bağımsız kopya sessizce ayrışabileceği için `test_kural_main_py_ile_ayni_mi` testi
`main.py`'nin **kaynak metnini okuyup** eşiklerin hâlâ aynı olduğunu doğrular.
Eşik korunan dosyada değişirse test kırılır.

## Ölçüm (224 kayıt, 21.07.2026 – 10.09.2026)

```
Toplam kayit          : 224
Replay edilebilir     : 102
Kapsam disi           : 122
Uyan                  : 102
Uymayan               : 0
Sadakat orani         : 100.00%
```

### Bulgu 1 — `decision_log` tek bir günlük değil, beş ayrı kayıt türü taşıyor

| kayıt türü | adet | durum |
|---|---|---|
| `god_mode` | 87 | kapsam dışı |
| `maa_5_katman` | 83 | **replay edilebilir** |
| `portfoy_sinyali` | 31 | kapsam dışı |
| `maa_4_katman_eski` (Chronos öncesi) | 19 | **replay edilebilir** |
| `llm_kaskadi` | 4 | kapsam dışı |

Yalnızca katman skoru taşıyan 102 kayıt yeniden üretilebilir. Kalan 122 kayıt
başka bir şey kaydediyor; bunları paydaya koymak oranı yapay olarak düşürürdü,
gizlemek ise kapsamı saklardı. İkisi de ayrı raporlanır.

### Bulgu 2 — %100 sadakat, kuralın tamamının doğrulandığı anlamına GELMİYOR

| karar dalı | üretimde görülen | durum |
|---|---|---|
| EKLE | 64 | sınandı |
| TUT | 30 | sınandı |
| BEKLE | 8 | sınandı |
| **DİKKAT ET** | **0** | **hiç sınanmadı** |

Üretim verisinde **hiçbir karar negatif toplam skor almamış** (gözlenen aralık
0 – 9). DİKKAT ET dalı kod içinde ulaşılabilir durumda (katman alt sınırlarının
toplamı -10 civarı) ama bu dönemde hiç tetiklenmemiş. Bu dal yalnızca birim
testleriyle kapsanmaktadır; sadakat oranı onun hakkında **bilgi vermez**.
Rapor bunu `>>> HIC SINANMADI <<<` satırıyla açıkça bildirir.

### Bulgu 3 — Negatif toplamın hiç görülmemesinin somut nedeni FAA katmanı

Katman skorlarının üretimde gözlenen aralığı:

| katman | n | min | max | negatif kayıt |
|---|---:|---:|---:|---:|
| taa | 95 | -1 | 1 | 25 |
| **faa** | **100** | **+1** | **5** | **0** |
| raa | 95 | -2 | 1 | 18 |
| saa | 68 | -1 | 1 | 5 |
| chronos | 79 | -1 | 1 | 23 |

FAA hiçbir kayıtta negatif olmamış ve en düşük değeri +1. Diğer dört katman
negatife inebiliyor, ancak FAA'nın taban katkısı toplamı yukarı çekiyor.
`score_faa` beş ölçütten üçünü (P/E, ROE, temettü) yalnızca **ödül** olarak
kullanıyor — ceza karşılıkları yok — bu yüzden yapısal olarak pozitife eğimli.
Bu bir hata tespiti değil, kural davranışının ölçülmüş bir gözlemidir; karar
kuralı Anayasa v4.4 gereği değiştirilmemiştir.

### Bulgu 4 — Kayıt "ölçülemedi" ayrımını koruyor

`layer_scores` içinde ölçülemeyen katmanlar `null` olarak saklanıyor (örn. id=216
CAT: `"saa": null`), sıfır olarak değil. Replay bu ayrımı korur: `null` katman
toplama girmez ve geçerli katman sayısına dahil edilmez. Bu, `232d1a0` ile kurulan
"ölçülemedi ≠ sıfır" değişmezinin veritabanı katmanında da tuttuğunun kanıtıdır.
Geçerli katman dağılımı: 1 katman → 1 kayıt, 2 → 7, 3 → 13, 4 → 22, 5 → 59.

## Şüphecilik turu — mutasyon testi

%100 sadakat, replay'in *her zaman "uydu" diyen* boş bir ölçüm olması ihtimalini
akla getirir. Dokuz mutasyon uygulandı; her biri hem birim testlerine hem gerçek
veriye karşı çalıştırıldı.

| # | mutasyon | test | gerçek veri sadakati |
|---|---|---|---|
| M1 | EKLE eşiği 4 → 5 | YAKALANDI (3 fail) | %100 → **%72.55** |
| M2 | DİKKAT eşiği -3 → -2 | YAKALANDI (2 fail) | %100 (veri bu dalı gezmiyor) |
| M3 | asgari katman 3 → 2 | YAKALANDI (3 fail) | %100 → **%93.14** |
| M4 | `null` katmanı sıfır say | YAKALANDI (5 fail) | çöküyor |
| M5 | her kayda "uydu" de | YAKALANDI (4 fail) | %100 |
| M6 | boş kümede sadakat 1.0 göster | YAKALANDI (2 fail) | %100 |
| M7 | kapsama her zaman tam görünsün | YAKALANDI (2 fail) | %100 |
| M8 | her şemayı replay edilebilir say | YAKALANDI (7 fail) | %100 → **%52.23** |
| M9 | kayıtlı toplamı sayıya çevirme | YAKALANDI (1 fail) | %100 |

**Hayatta kalan mutasyon yok (0/9).** M1, M3 ve M8 ayrıca gerçek veri oranını da
değiştiriyor — yani %100 sonucu ölçüme duyarlıdır, boş bir onay değildir.

M2'nin gerçek veriyi hiç değiştirmemesi Bulgu 2'nin bağımsız doğrulamasıdır:
veri kümesi DİKKAT ET eşiğine hiç yaklaşmıyor.

## Sonuç

Sistem, katman skoru kaydettiği 102 kararın **tamamını** kayıtlı katman
skorlarından birebir yeniden üretebiliyor — karar kodu ve toplam skor dahil.
Kayıt ile kural arasında ayrışma bulunamadı.

İki sınır açıkça belirtilir: (1) DİKKAT ET dalı üretim verisiyle hiç
doğrulanmamıştır, (2) `decision_log` kayıtlarının %54'ü (122/224) katman skoru
taşımadığı için bu denetimin kapsamı dışındadır.

## Üretilen dosyalar

- `maa/src/karar_replay.py` — replay kuralı, şema sınıflandırması, kapsama ölçümü
- `maa/src/replay_calistir.py` — CLI rapor üreticisi (uyuşmazlık varsa çıkış kodu 1)
- `maa/src/test_karar_replay.py` — 38 test

Yeniden üretmek için:

```bash
docker exec alphawise-timescaledb psql -U alphawise -d alphawise_db -At -c "
SELECT json_agg(t)::text FROM (SELECT id,ticker,decision,total_score,layer_scores,
  decided_at::text AS decided_at, source FROM decision_log ORDER BY id) t;" > /tmp/dl.json
docker run --rm --network none -v "$PWD/maa/src:/app:ro" -v /tmp/dl.json:/tmp/dl.json:ro \
  -w /app alphawise-test/maa:latest python replay_calistir.py /tmp/dl.json
```
