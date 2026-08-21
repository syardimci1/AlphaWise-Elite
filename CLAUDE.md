# AlphaWise-Elite Claude Code Kuralları

## BÜTÇE ONAY KURALI

Bu kural LLMQuant kredileri, FMP API kotaları ve gelecekte eklenecek her ücretli/sınırlı kaynak için geçerlidir.

1. **Herhangi bir kredi/maliyet gerektiren işlem için istenen kapsam mevcut bütçeyi aşıyorsa: İCRA ETME.**
2. Bütçeye sığan alternatif bir kapsam ÖNERİLEBİLİR ama ASLA otomatik uygulanamaz.
3. Kullanıcıdan açık onay (senaryo numarası veya "evet uygula" gibi net bir yanıt) gelmeden hiçbir kredi harcanamaz.
4. "Otomatik kapsam küçültme" (bütçeye sığan en yakın alt senaryoyu bulup çalıştırma) YASAKTIR — bu yol kod seviyesinde de kapatılmalıdır.
5. Onay bekleme mesajı şu bilgileri içermelidir: gereken kredi, mevcut bakiye, açık, ve önerilen alternatif(ler).

## KORUNAN DOSYALAR

Aşağıdaki dosyalara TEK SATIR bile dokunulamaz:
- `maa/src/cascade.py`
- `maa/src/main.py`
- `maa/src/llmquant_client.py`

## KARAR KODLARI

`main.py`'deki mevcut /decide ve /narrative-verified karar kodları (EKLE/TUT/BEKLE/DİKKAT ET) DEĞİŞMEYECEK — ticari ürün Anayasa v4.4'te kalacak.

## DİL KURALLARI

KESİN İFADE YASAK: 'yukarı gidecek', 'al', 'sat', 'şu fiyattan gir' gibi emir/kesinlik bildiren dil KULLANILMAYACAK.
