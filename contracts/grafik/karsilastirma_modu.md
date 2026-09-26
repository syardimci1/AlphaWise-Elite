# KARŞILAŞTIRMA MODU SÖZLEŞMESİ — grafik terminali

**Tarih:** 25.09.2026 · **Dayanak:** ADR-6 (`contracts/grafik/ADR.md`) · **Keşif:** `kanit/karsilastirma/faz1_kesif.md`
**Kalıcılık dayanağı:** ADR-5 / `kalicilik_sozlesmesi.md` (aynı desen, üçüncü tür)

Terimler: **ana sembol** = terminalin `symbol` prop'u; **ek sembol** = kullanıcının karşılaştırmaya eklediği sembol;
**grup** = ana sembol + ek semboller.

## C1 — Normalize formül ve ortak taban

- **Taban tarihi** = grubun TÜM serilerinin geçerli (sonlu, > 0) kapanışa sahip olduğu **ilk takvim günü**.
  Serilerin kendi ilk günleri farklıysa (biri daha geç başlıyorsa) taban en geç başlayanın ilk ortak günüdür.
- Her seri için `yüzde_t = (kapanış_t / kapanış_taban − 1) × 100`. Taban gününde her seri **tam olarak %0**'dır;
  tüm seriler aynı tarihte, aynı noktadan başlar.
- Taban öncesi barlar grafiğe **girmez**; sembol başına sayısı ve tarih aralığı lejantta yazılır ("… bar ortak başlangıç öncesinde").
- Taban **sabittir**: kaydırma/yakınlaştırma onu değiştirmez (kütüphanenin "ilk görünür değer" yüzde modu bu yüzden kullanılmaz).
- Ortak gün yoksa (tarih aralıkları hiç kesişmiyor) grafik çizilmez, "ortak işlem günü yok" nedeni gösterilir.
- Girdi kapanış fiyatıdır; temettü/bölünme düzeltmesi **iddia edilmez** (kaynak karışık, FAZ 1 §3.2). Tek günde
  |değişim| > %40 olan günler sayılır ve "bölünme veya veri hatası olabilir" diye işaretlenir.
- Karşılaştırma **günlük** kapanışlarla yapılır; haftalık/aylık dilim karşılaştırmada kullanılmaz (ADR-6 §dilim).

## C2 — Sembol limiti

- Grup en fazla **3 sembol** (ana + 2 ek), en az 2 sembolle karşılaştırma çizilir.
- 3 doluyken ekleme **reddedilir** ve görünür bir metinle söylenir; en eski sembol otomatik ÇIKARILMAZ (ADR-6 §limit).
  Ekleme düğmesi dolulukta devre dışıdır ve nedeni yanında yazar.
- Reddedilen diğer girdiler (hepsi görünür metinle): geçersiz ticker biçimi, ana sembolün kendisi, zaten ekli sembol
  (büyük/küçük harf ve boşluktan bağımsız: `msft `, `MSFT` aynıdır).

## C3 — Renk ve lejant

- Renkler sabit sırayla ve **varlığa** bağlı atanır: ana sembol her zaman yuva 0; ek sembol eklendiği anda en düşük
  boş yuvayı alır ve çıkarılana kadar korur (bir sembolü çıkarmak diğerinin rengini değiştirmez).
- Palet (koyu yüzey `#0f172a`): `#3987e5` mavi · `#d95926` turuncu · `#199e70` yeşil-mavi. Doğrulama çıktısı
  `kanit/karsilastirma/palet_dogrulama.txt` (tüm çiftler: CVD ΔE ≥ 9,4, normal görüş ΔE ≥ 20,9, kontrast ≥ 3:1).
- Lejant grafiğin **üstünde, her zaman görünür** HTML'dir (üzerine gelmeye bağlı değildir): renk karesi + sembol +
  gösterilen tarihteki yüzde + notlar. Fiyat ekseninde son değer etiketi sembol adını taşır. Kimlik yalnızca renge bağlı değildir.
- Metinler renkli yazılmaz; renk yalnızca yanındaki karede/çizgide taşınır.

## C4 — Veri boşluğu

- Zaman ekseni = taban sonrası grubun **herhangi bir** serisinde barı olan günlerin birleşimi.
- Bir seride o gün bar yoksa (ya da kapanış geçersizse) o gün **"veri yok"**tur:
  - değer üretilmez (enterpolasyon YOK, son değer taşıma YOK);
  - çizgi o günü köprülemez: boşluktan önceki son noktanın segment rengi saydamdır (ölçülen mekanizma, FAZ 1 §2.1);
  - lejantta sembol başına "N gün veri yok" sayısı ve ilk birkaç tarih yazar;
  - imleç o güne geldiğinde lejantta o sembol için "veri yok" yazar.
- Serinin son barından sonraki günler boşluk sayılmaz; lejantta "son veri: TARİH" yazar.
- **Hiçbir seride barı olmayan gün** eksende yer almaz (hafta sonu/tatil ile aynı muamele). Takvim verisi olmadan
  "orada bar olmalıydı" denemez; bu bir sınırdır ve iddia edilmez.
- Yalnızca tek bir günlük "ada" (iki yanı boşluk) çizgi olarak görünmez; değeri imleçte okunur, sayımda kaybolmaz.

## C5 — Kalıcılık

```
alphawise:grafik:karsilastirma:v1:<kimlik>:<ANA_SEMBOL>
{ "v": 1, "mod": "tek" | "karsilastirma", "semboller": [{ "sembol": "MSFT", "yuva": 1 }], "guncelleme_utc": 1758800000000 }
```

- Anahtar `adAlaniAnahtari` ile üretilir (ADR-5; kaçışlama, büyük harf normalizasyonu, kimliksiz yazım yok).
- Yazım 300 ms debounce'lu (`GecikmeliKayit`), `pagehide`/gizlenme/kaldırmada boşaltılır; yükleme kapısı anahtarın
  tamamıdır (H-1); yüklenen içerik geri yazılmaz (H-5).
- Okuma yan etkisizdir. Göç tablosu `kalicilik_sozlesmesi.md` C4 ile aynı (bozuk → sıfırla + uyarı; bilinmeyen `v` → sıfırla + uyarı);
  ek olarak geçersiz, yinelenen, ana sembole eşit, 2'yi aşan ya da yuvası çakışan öğeler ayıklanır ve sayısı uyarıya yazılır.
- "Kayıtlı ayarları sıfırla" bu anahtarı da siler; `storage` olayı bu anahtar için de uyarı gösterir.

## C6 — Mod geçişi

- İki mod: **Tek sembol** / **Karşılaştırma** (`aria-pressed` düğmeler). Geçiş hiçbir veriyi silmez:
  - tek-sembol grafiği karşılaştırma modunda **kaldırılmaz, gizlenir** → görünüm (yakınlaştırma/kaydırma), çizimler,
    geri al yığını, göstergeler, zaman dilimi aynen kalır;
  - karşılaştırma listesi tek-sembol modunda korunur; geri dönüldüğünde aynı semboller, aynı renklerle gelir;
  - ek sembollerin çekilmiş verisi oturum boyunca önbellekte tutulur (geçişte yeniden istek yok).
- Karşılaştırma modunda çizim/gösterge/dilim/PNG denetimleri gizlenir ve Delete/Backspace çizim silmez
  (görünmeyen bir çizimi silmek görünmez bir veri kaybı olurdu).
- Karşılaştırma modunda ek sembol yoksa (ya da ek sembollerin hiçbirinin verisi yoksa) **tek seri gösterimine düşülür**
  (mum grafiği görünür) ve nedeni yazılır.

## Erişilebilirlik ve mobil (Y11)

- Sembol ekleme: etiketli `<input>` + `<button>`, bir `<form>` içinde (Enter ile gönderilir). Çıkarma: sembol başına
  `aria-label="Karşılaştırmadan çıkar: MSFT"` taşıyan yerel `<button>`. Reddetme/ekleme sonucu `role="status"` ile duyurulur.
- 390 px genişlikte yatay kaydırma yok; denetimler `flex-wrap` ile satır kırar.
