"""IZOLE BIRIM TESTI - satir_sonu_onar.py.

Gercek veriye DOKUNMAZ; her senaryo kendi gecici dizininde kurulur.
"""
import os
import tempfile

import satir_sonu_onar as onar

SATIRLAR = [
    b"date,open,high,low,close,volume,factor",
    b"2026-08-21,100.0,110.0,90.0,105.0,900,1.0",
    b"2026-08-24,101.0,111.0,91.0,106.0,950,1.0",
]


def yaz(yol, satir_sonlari):
    """Verilen satir sonu LISTESIYLE (satir basina biri) dosya kur."""
    with open(yol, "wb") as f:
        for i, satir in enumerate(SATIRLAR):
            f.write(satir + satir_sonlari[i])


def test_saf_lf_dokunulmaz():
    print("\n===== saf LF dosya - DOKUNULMAMALI =====")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "T.csv")
        yaz(p, [b"\n"] * 3)
        onceki = open(p, "rb").read()
        etiket = onar.normalize_dosya(p)
        sonraki = open(p, "rb").read()
        ok = etiket == "atlandi_karisik_degil" and onceki == sonraki
        print(f"  etiket={etiket}  byte_duzeyinde_ayni={onceki == sonraki}  -> {'OK' if ok else 'FAIL'}")
        return ok


def test_saf_crlf_dokunulmaz():
    print("\n===== saf CRLF dosya - DOKUNULMAMALI =====")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "T.csv")
        yaz(p, [b"\r\n"] * 3)
        onceki = open(p, "rb").read()
        etiket = onar.normalize_dosya(p)
        sonraki = open(p, "rb").read()
        ok = etiket == "atlandi_karisik_degil" and onceki == sonraki
        print(f"  etiket={etiket}  byte_duzeyinde_ayni={onceki == sonraki}  -> {'OK' if ok else 'FAIL'}")
        return ok


def test_karisik_dosya_hedefin_kendi_duzenine_normalize_edilir():
    print("\n===== karisik dosya (CRLF baslik + LF eklenen satir) - DUZELTILMELI =====")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "T.csv")
        yaz(p, [b"\r\n", b"\r\n", b"\n"])  # ilk iki CRLF, sonuncusu LF -> karisik
        onceki_ham = open(p, "rb").read()
        assert onar.karisik_mi(onceki_ham)

        etiket = onar.normalize_dosya(p)
        sonraki_ham = open(p, "rb").read()

        karisik_kaldi = onar.karisik_mi(sonraki_ham)
        hepsi_crlf = sonraki_ham.count(b"\r\n") == sonraki_ham.count(b"\n")
        deger_ayni = onceki_ham.replace(b"\r\n", b"\n") == sonraki_ham.replace(b"\r\n", b"\n")

        ok = etiket == "duzeltildi" and not karisik_kaldi and hepsi_crlf and deger_ayni
        print(f"  etiket={etiket}  karisik_kaldi={karisik_kaldi}  hepsi_crlf={hepsi_crlf}"
              f"  deger_ayni={deger_ayni}  -> {'OK' if ok else 'FAIL'}")
        return ok


def test_ayristirilamayan_dosyaya_dokunulmaz():
    print("\n===== bozuk/ayristirilamayan CSV - DOKUNULMAMALI (fail-closed) =====")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "T.csv")
        # baslikta 2, ikinci govde satirinda 4 sutun -> pandas C parser
        # "Error tokenizing data" ile hata verir (fazla alan, az alan gibi
        # NaN ile doldurulup sessizce gecistirilemez)
        with open(p, "wb") as f:
            f.write(b"a,b\r\n1,2\n3,4,5,6\r\n")
        onceki = open(p, "rb").read()
        etiket = onar.normalize_dosya(p)
        sonraki = open(p, "rb").read()
        ok = etiket == "atlandi_ayristirilamadi" and onceki == sonraki
        print(f"  etiket={etiket}  byte_duzeyinde_ayni={onceki == sonraki}  -> {'OK' if ok else 'FAIL'}")
        return ok


sonuclar = [
    test_saf_lf_dokunulmaz(),
    test_saf_crlf_dokunulmaz(),
    test_karisik_dosya_hedefin_kendi_duzenine_normalize_edilir(),
    test_ayristirilamayan_dosyaya_dokunulmaz(),
]
print("\nTEST: " + ("PASS" if all(sonuclar) else "FAIL"))
raise SystemExit(0 if all(sonuclar) else 1)
