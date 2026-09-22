"""
lambda=0 IZOLASYON TESTI - senate-lda-service (20.09.2026, madde 35).

congress-trading-service/sec-edgar-13f-service ile AYNI desen: bu
servisler runtime icerik filtresi (insider-trading-service'in
lambda_sifir.py'si) TASIMAZ - onun yerine MIMARI izolasyon kanitlanir:
MAA'nin karar zincirinin (maa/src/main.py, cascade.py) bu servisi HICBIR
YERDEN cagirmadigi/import etmedigi AST ile dogrulanir. Bu, kutsal
main.py'ye DOKUNMADAN, onu SALT-OKUNUR tarayarak yapilir.
"""
import ast
import pathlib

KOK = pathlib.Path(__file__).resolve().parents[2]   # .../AlphaWise-Elite


def _kaynaklarda_gecen_stringler(dosya: pathlib.Path) -> set:
    """Bir Python dosyasindaki TUM string literal + import edilen modul
    adlarini toplar - hem 'senate-lda-service' hem 'senate_lda' gibi
    olasi cagri bicimlerini yakalamak icin."""
    kaynak = dosya.read_text(encoding="utf-8")
    agac = ast.parse(kaynak)
    stringler = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Constant) and isinstance(d.value, str):
            stringler.add(d.value)
        elif isinstance(d, ast.Import):
            stringler.update(a.name for a in d.names)
        elif isinstance(d, ast.ImportFrom) and d.module:
            stringler.add(d.module)
    return stringler


def test_maa_main_bu_servisi_TANIMIYOR():
    """Kutsal dosya OKUNUR (degistirilmez) - icinde senate-lda gecen
    hicbir string/import olmamali."""
    maa_main = KOK / "maa" / "src" / "main.py"
    assert maa_main.exists(), "kutsal dosya bulunamadi - yol degismis olabilir"
    stringler = _kaynaklarda_gecen_stringler(maa_main)
    for s in stringler:
        assert "senate-lda" not in s.lower() and "senate_lda" not in s.lower(), (
            f"maa/src/main.py 'senate-lda' referansi TASIYOR: {s!r}")


def test_maa_cascade_bu_servisi_TANIMIYOR():
    cascade = KOK / "maa" / "src" / "cascade.py"
    if not cascade.exists():
        return   # dosya yoksa test konusu yok, hata sayilmaz
    stringler = _kaynaklarda_gecen_stringler(cascade)
    for s in stringler:
        assert "senate-lda" not in s.lower() and "senate_lda" not in s.lower(), (
            f"maa/src/cascade.py 'senate-lda' referansi TASIYOR: {s!r}")


def test_bu_servis_MAA_karar_koduna_YAZMIYOR():
    """Ters yon: bu servisin kendi kaynagi da EKLE/TUT/BEKLE/DIKKAT ET
    gibi MAA karar kodlari URETMEMELI - salt gozlem/rapor servisidir."""
    yasakli_kodlar = {"EKLE", "DIKKAT ET"}   # TUT/BEKLE cok genel kelimeler, atlanir
    kendi_dizin = pathlib.Path(__file__).resolve().parent.parent
    for py in kendi_dizin.glob("*.py"):
        kaynak = py.read_text(encoding="utf-8")
        agac = ast.parse(kaynak)
        for d in ast.walk(agac):
            if isinstance(d, ast.Constant) and isinstance(d.value, str):
                assert d.value not in yasakli_kodlar, (
                    f"{py.name} MAA karar kodu URETIYOR: {d.value!r}")


def test_docker_compose_yeni_servis_MAA_ile_AYNI_agda_ZORUNLU_DEGIL():
    """Belgesel test: bu servisin docker-compose girdisi (varsa) 'links'/
    'depends_on' ile maa/taa servisine BAGLANMAMALI - bagimsizligi
    altyapi seviyesinde de korur."""
    compose = KOK / "docker-compose.yml"
    if not compose.exists():
        return
    metin = compose.read_text(encoding="utf-8")
    if "senate-lda:" not in metin:
        return   # henuz compose'a eklenmemis olabilir - ayri adim
    blok_basi = metin.index("senate-lda:")
    sonraki_servis = metin.find("\n  ", blok_basi + 20)
    blok = metin[blok_basi:sonraki_servis if sonraki_servis != -1 else None]
    assert "depends_on" not in blok, "senate-lda servisi baska bir servise BAGIMLI olmamali"
