import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import filtre


def test_tavsiye_iceren_metin_tetiklenir():
    sonuc = filtre.denetle("Bu hisse olumlu sinyaller vermektedir, alim firsati olabilir.")
    assert sonuc["tetiklendi"] is True
    assert "AL/SAT" not in sonuc["guvenli_metin"]
    assert "tavsiyesi degildir" in sonuc["guvenli_metin"].lower()


def test_temiz_metin_tetiklenmez():
    sonuc = filtre.denetle("Sirket bugun ceyrek sonuclarini acikladi, gelir yuzde 5 artti.")
    assert sonuc["tetiklendi"] is False
    assert "ceyrek sonuclarini" in sonuc["guvenli_metin"]


def test_ingilizce_tavsiye_kelimeleri_yakalanir():
    sonuc = filtre.denetle("Analysts recommend to buy this stock, price target raised.")
    assert sonuc["tetiklendi"] is True


def test_hold_kelimesi_yakalanir():
    sonuc = filtre.denetle("We suggest investors hold their position for now.")
    assert sonuc["tetiklendi"] is True


def test_feragat_metni_her_zaman_eklenir():
    temiz = filtre.denetle("Bugun onemli bir gelisme bulunamadi.")
    tetiklenen = filtre.denetle("satin alma firsati")
    assert filtre.FERAGAT_METNI in temiz["guvenli_metin"]
    assert filtre.FERAGAT_METNI in tetiklenen["guvenli_metin"]


def test_bekle_kelimesi_yakalanir():
    sonuc = filtre.denetle("Yatirimcilarin bu asamada beklemesi onerilir.")
    assert sonuc["tetiklendi"] is True


def test_hedef_fiyat_yakalanir():
    sonuc = filtre.denetle("Analistler hedef fiyati 250 dolara yukseltti.")
    assert sonuc["tetiklendi"] is True


def test_bos_metin_tetiklenmez_ve_hata_vermez():
    sonuc = filtre.denetle("")
    assert sonuc["tetiklendi"] is False
