"""
ALPHAWISE - Artimli Veri Guncelleme (16.08.2026 - v3, Polars)
Tarih karsilastirmasi Polars'in kendi datetime tipiyle DEGIL, guvenli
string->Python datetime cevrimiyle yapilir (Polars/pandas datetime
etkilesiminde sessiz hata riskini onlemek icin).
"""
import polars as pl
import pandas as pd  # sadece defeatbeta_api'nin pandas DataFrame donmesi icin
import json, os
from datetime import datetime, date, timedelta

PROGRESS_FILE = "/app/csv_data/progress.json"
DATA_DIR = "/app/csv_data/us_data"

# ---------------------------------------------------------------------------
# ON-YAYIN (PRELIMINARY) BAR DUZELTMESI — 04.09.2026
#
# OLCULEN SORUN
#   Dosyalarin 6.529/6.742'sinin son bari 2026-08-27 idi. O gunun barlari
#   saglayicidan CEKILDIGI ANDA henuz NIHAI DEGILDI: 30 likit sembolluk
#   ornekte son barin %66,7'si saglayicinin bugunku nihai degerinden farkli
#   cikti. Farkin YONU tek tarafli: bizim [low, high] araligimiz nihai
#   araligin ALT KUMESI (orn. RDN 08-27 high 36,74 -> 37,00; SE 118,875 ->
#   118,99; FLUT 98,98 -> 99,13). Yani bar, gunun tam aralik bilgisi
#   olusmadan yazilmis.
#
#   BIR ONCEKI barlarda (g-1 ... g-10) fark orani %0,0 — yani bozulma
#   YALNIZCA her kosuda yazilan SON bara ozgu.
#
# KOK NEDEN (iki parca)
#   1) Ust tarih siniri yoktu: "date > son_tarih" kosulu, seansi HENUZ
#      BITMEMIS bir gunun barini da kabul ediyordu.
#   2) Yazma bicimi salt-EKLEME idi: bir kez yazilan satir bir daha
#      okunmuyor/duzeltilmiyordu. Saglayici barini sonradan revize etse
#      bile bizdeki ON-YAYIN kopyasi KALICI olarak donuyordu.
#
# COZUM
#   1) BITMEMIS_SEANS_KORUMASI: yalnizca tarihi BUGUNDEN KUCUK barlar
#      yazilir. Suren seansin yarim bari asla diske inmez.
#   2) REVIZYON_PENCERESI: son N gunluk bolum her kosuda saglayicidan
#      YENIDEN okunur ve dosyada UZERINE YAZILIR. Boylece saglayicinin
#      gec gelen duzeltmeleri bize de yansir; bar artik "donmus" kalmaz.
#   3) BAR BUTUNLUGU DOGRULAMASI: high < max(open,close) veya
#      low > min(open,close) olan IMKANSIZ barlar yazilmaz. Olculdu:
#      40 ihlalli ornegin 30'u saglayicinin KENDI bozuk verisiydi
#      (warrant/unit ve 1990'lar tarihi). Bu barlar TAA'nin formasyon
#      modulunde golge uzunlugunu NEGATIF yapiyor ve ATR'yi bozuyor;
#      eksik bar, imkansiz bardan durusttur (projenin "olculemedi"
#      ilkesi).
#
# Kanit: data-fetcher/scripts/_test_on_yayin_bar.py
# ---------------------------------------------------------------------------
REVIZYON_PENCERESI_GUN = 5


def bar_butunlugu_gecerli(o, h, l, c):
    """Bar ici tutarlilik: high tum fiyatlarin ustunde, low altinda olmali.

    'open' bilerek de kontrol edilir: olculen 4.649 ihlalin 4.314'unde
    tutarsiz alan tam olarak 'open' idi (high/low/close kendi arasinda
    tutarliydi).
    """
    try:
        o, h, l, c = float(o), float(h), float(l), float(c)
    except (TypeError, ValueError):
        return False
    if any(x != x for x in (o, h, l, c)):  # NaN
        return False
    return h >= max(o, c) and l <= min(o, c) and h >= l

with open(PROGRESS_FILE) as f:
    progress = json.load(f)

completed = progress["completed"]
print(f"Artimli guncelleme icin kontrol edilecek: {len(completed)} hisse", flush=True)

guncellenen = 0
zaten_guncel = 0
hata = 0
revize_edilen_satir = 0
reddedilen_bozuk_bar = 0
satir_kaybi_atlanan = 0

# Suren seansin yarim bari asla yazilmaz: sinir BUGUN'dur (haric).
BUGUN = date.today()
REVIZYON_SINIRI = BUGUN - timedelta(days=REVIZYON_PENCERESI_GUN)

for i, ticker in enumerate(completed):
    csv_path = f"{DATA_DIR}/{ticker}.csv"
    if not os.path.exists(csv_path):
        continue
    try:
        mevcut = pl.read_csv(csv_path)
        if mevcut.is_empty():
            continue

        son_tarih_str = str(mevcut["date"].max())
        son_tarih = datetime.strptime(son_tarih_str[:10], "%Y-%m-%d")

        # ESKI KOSUL "(now - son_tarih).days <= 2: continue" KALDIRILDI.
        # Bu kosul, on-yayin barin kalici olarak donmasinin ikinci yarisiydi:
        # bar yazildiktan sonraki 2 gun boyunca dosya HIC acilmiyordu, 2 gun
        # sonra da salt-ekleme mantigi o bara zaten dokunmuyordu.
        #
        # Gecerli bir atlama kosulu YOKTUR: son bar revizyon penceresi
        # ICINDEyse yeniden okunmalidir (duzelmis olabilir), penceresi
        # DISINDAysa zaten eskidir ve yeni bar eklenmelidir. Her iki durumda
        # da saglayiciya bakmak gerekir. "Degisiklik yok" durumu asagida,
        # veri karsilastirildiktan SONRA tespit edilir (zaten_guncel).

        from defeatbeta_api.data.ticker import Ticker
        t = Ticker(ticker)
        yeni = t.price()
        if yeni is None or yeni.empty:
            continue
        yeni = yeni.rename(columns={"report_date": "date"})
        yeni["date"] = pd.to_datetime(yeni["date"])
        yeni["factor"] = 1.0
        # SUTUN SIRASI HATASI DUZELTMESI (23.08.2026):
        # Depoda IKI farkli baslik duzeni var:
        #   A) date,open,high,low,close,volume,factor   (defeatbeta toplu cekim)
        #   B) date,open,close,high,low,volume,factor   (Tiingo/qlib yolu)
        # Bu satir onceden A duzenini SABIT KODLUYOR ve header=False ile
        # ekliyordu; B tipi dosyalarda close/high/low sutunlari kayiyor ve bar
        # "high < max(open,close)" gibi imkansiz degerler aliyordu
        # (2.589 dosyada 17.642 satir bu sekilde bozulmustu).
        # Cozum: sutun sirasi, hedef dosyanin KENDI basligindan okunur.
        hedef_sutunlar = list(mevcut.columns)
        eksik = [s for s in hedef_sutunlar if s not in yeni.columns]
        if eksik:
            raise ValueError(f"{ticker}: kaynakta eksik sutun {eksik}")
        # --- BITMEMIS SEANS KORUMASI ---------------------------------------
        # Yalnizca tarihi BUGUNDEN KUCUK barlar kabul edilir. Suren seansin
        # yarim bari (open belli, high/low henuz olusmamis) diske inmez.
        yeni = yeni[yeni["date"].dt.date < BUGUN]

        # --- REVIZYON PENCERESI --------------------------------------------
        # Salt-ekleme yerine: son N gunluk bolum saglayicidan yeniden okunur
        # ve dosyada UZERINE YAZILIR; oncesi oldugu gibi korunur.
        #
        # Kesme noktasi BUGUNE degil, DOSYANIN KENDI son tarihine gore
        # alinir. Aksi halde (bugune gore alinirsa) dosya bugunden N gunden
        # daha eskiyse son bar pencerenin DISINDA kalir ve tam da duzeltmek
        # istedigimiz on-yayin bar yeniden okunmaz.
        kesme = son_tarih - timedelta(days=REVIZYON_PENCERESI_GUN)
        yeni = yeni[yeni["date"] > kesme][hedef_sutunlar]

        # --- BAR BUTUNLUGU DOGRULAMASI -------------------------------------
        # Imkansiz barlar (saglayici kaynakli olsa bile) yazilmaz.
        if len(yeni) > 0:
            gecerli = yeni.apply(
                lambda r: bar_butunlugu_gecerli(r["open"], r["high"],
                                                r["low"], r["close"]),
                axis=1)
            reddedilen_bozuk_bar += int((~gecerli).sum())
            yeni = yeni[gecerli]

        if len(yeni) > 0:
            # SATIR SONU HATASI DUZELTMESI (24.08.2026):
            # Depoda IKI satir sonu birlikte yasiyor (olculdu, 6.755 dosya):
            #   LF   (\n)   -> 4.011 dosya (defeatbeta toplu cekim)
            #   CRLF (\r\n) -> 2.744 dosya (Tiingo/qlib yolu)
            # pandas to_csv varsayilan olarak LF yazar; CRLF bir dosyaya
            # eklenince dosya KARISIK satir sonlu kaliyordu. Olculen etki:
            # 104 dosya karisik hale gelmis ve DuckDB'nin CSV lehce sezicisi
            # bu dosyalari ayristiramaz olmustu ("Error when sniffing file").
            # Cozum, yukaridaki sutun sirasi duzeltmesiyle AYNI ilkeyi izler:
            # bicim karari sabit kodlanmaz, hedef dosyanin KENDISINDEN okunur.
            # Kanit: data-fetcher/scripts/_test_satir_sonu.py
            with open(csv_path, "rb") as f:
                satir_sonu = "\r\n" if f.readline().endswith(b"\r\n") else "\n"

            # Revizyon penceresindeki ESKI satirlar dusurulur, yerine
            # saglayicinin guncel hali yazilir. Salt-ekleme (mode="a")
            # ARTIK KULLANILAMAZ: uzerine yazma gerekiyor. Baslik duzeni ve
            # satir sonu, onceki iki duzeltmedeki ilkeyle yine HEDEF
            # DOSYANIN KENDISINDEN alinir.
            # NOT: polars'in to_pandas()'i pyarrow gerektiriyor ve bu imajda
            # pyarrow YOK. Yeni bir bagimlilik eklemek yerine eski satirlar
            # dogrudan pandas ile okunur.
            eski = pd.read_csv(csv_path)
            eski["date"] = pd.to_datetime(eski["date"])
            korunan = eski[eski["date"] <= kesme]
            revize_edilen_satir += len(eski) - len(korunan)

            birlesik = pd.concat([korunan[hedef_sutunlar], yeni],
                                 ignore_index=True)
            birlesik = birlesik.sort_values("date")
            birlesik["date"] = pd.to_datetime(birlesik["date"]).dt.strftime("%Y-%m-%d")

            # FAIL-CLOSED KORUMASI: revizyon penceresi UZERINE YAZDIGI icin,
            # saglayicinin o pencerede bizde olan bir tarihi vermemesi
            # (gecici bosluk, sembol degisikligi) satir KAYBINA yol acabilir.
            # Boyle bir durumda dosyaya HIC dokunulmaz ve durum raporlanir —
            # eksik veriyle sessizce devam etmek yerine hicbir sey yapmamak.
            if len(birlesik) < len(eski):
                print(f"ATLANDI ({ticker}): revizyon penceresi satir kaybina "
                      f"yol acacakti ({len(eski)} -> {len(birlesik)})", flush=True)
                satir_kaybi_atlanan += 1
                continue

            # Atomik yazim: yarim kalan bir kosu dosyayi bozmasin.
            gecici = csv_path + ".tmp"
            birlesik.to_csv(gecici, index=False, lineterminator=satir_sonu)
            os.replace(gecici, csv_path)
            guncellenen += 1
        else:
            zaten_guncel += 1

    except Exception as e:
        print(f"HATA ({ticker}): {type(e).__name__}: {e}", flush=True)
        hata += 1
        continue

    if (i + 1) % 500 == 0:
        print(f"  {i+1}/{len(completed)} kontrol edildi | guncellenen: {guncellenen}", flush=True)

print(f"\nTAMAMLANDI. Guncellenen: {guncellenen} | Zaten guncel: {zaten_guncel} | Hata: {hata}", flush=True)
print(f"Revizyon penceresinde yeniden yazilan satir: {revize_edilen_satir}", flush=True)
print(f"Butunluk ihlali nedeniyle REDDEDILEN bar     : {reddedilen_bozuk_bar}", flush=True)
print(f"Satir kaybi riski nedeniyle ATLANAN dosya   : {satir_kaybi_atlanan}", flush=True)
