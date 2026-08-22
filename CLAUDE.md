# AlphaWise-Elite Claude Code Kuralları

## BÜTÇE ONAY KURALI

Bu kural LLMQuant kredileri, FMP API kotaları ve gelecekte eklenecek her ücretli/sınırlı kaynak için geçerlidir.

1. **Herhangi bir kredi/maliyet gerektiren işlem için istenen kapsam mevcut bütçeyi aşıyorsa: İCRA ETME.**
2. Bütçeye sığan alternatif bir kapsam ÖNERİLEBİLİR ama ASLA otomatik uygulanamaz.
3. Kullanıcıdan açık onay (senaryo numarası veya "evet uygula" gibi net bir yanıt) gelmeden hiçbir kredi harcanamaz.
4. "Otomatik kapsam küçültme" (bütçeye sığan en yakın alt senaryoyu bulup çalıştırma) YASAKTIR — bu yol kod seviyesinde de kapatılmalıdır.
5. Onay bekleme mesajı şu bilgileri içermelidir: gereken kredi, mevcut bakiye, açık, ve önerilen alternatif(ler).

## SORUNU SORMADAN DÜZELTME KURALI

Bir sorun, hata veya şüpheli nokta bulunduğunda kullanıcıya "düzelteyim mi?" diye SORULMAZ. Doğrudan düzeltilir, test edilir ve sonuç **"düzelttim, işte kanıt"** biçiminde, gerçek komut çıktısıyla birlikte bildirilir.

Tek istisna yukarıdaki BÜTÇE ONAY KURALI'dır: kredi/ücret harcayan bir işlem (LLM çağrısı, ücretli API kotası) hâlâ açık onay gerektirir. Yani "sorma, düzelt" teknik düzeltmeler için geçerlidir, para harcamak için değil.

## KANITLANMAMIŞ KOD PUSH EDİLMEZ KURALI

Hiçbir modül, gerçekten çalıştığı bir testle kanıtlanmadan commit veya push EDİLMEZ.

1. Bir değişikliğin bir kısmı doğrulanmış, bir kısmı şüpheli/doğrulanmamışsa: doğrulanmamış kısım push DIŞINDA bırakılır, yalnızca kanıtlanmış parçalar gönderilir.
2. Hangi kısmın neden bekletildiği açıkça belirtilir.
3. Commit kapsamı testlerin kapsadığı alana göre belirlenir — "nasılsa birlikte yazıldı" gerekçesiyle doğrulanmamış dosyaları aynı commit'e eklemek YASAKTIR.

## KORUNAN DOSYALAR

Aşağıdaki dosyalara TEK SATIR bile dokunulamaz:
- `maa/src/cascade.py`
- `maa/src/main.py`
- `maa/src/llmquant_client.py`

## KARAR KODLARI

`main.py`'deki mevcut /decide ve /narrative-verified karar kodları (EKLE/TUT/BEKLE/DİKKAT ET) DEĞİŞMEYECEK — ticari ürün Anayasa v4.4'te kalacak.

## DİL KURALLARI

KESİN İFADE YASAK: 'yukarı gidecek', 'al', 'sat', 'şu fiyattan gir' gibi emir/kesinlik bildiren dil KULLANILMAYACAK.
