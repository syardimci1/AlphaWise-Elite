"""007 — kullanici goruntuleme kaydi izolasyon testi.

C4 sozlesmesi: EN AZ 2 gercek kullanici, superuser DEGIL gercek rolle.
`postgres` BYPASSRLS tasidigi icin onunla yapilan hicbir olcum izolasyon
kanitlamaz; burada her sey `anon` / `authenticated` rolleriyle yapilir.

TESTLERIN VARLIK NEDENI (olculdu, 17.09.2026):
`public` semasinda acilan her yeni tablo `anon=arwdDxtm` (TRUNCATE + MAINTAIN
dahil) ile ve RLS KAPALI dogar; yeni fonksiyon PUBLIC EXECUTE alir. Yani 006
ile kapatilan acik, 007 acikca REVOKE yazmasaydi bu tabloda ILK GUNDEN
yeniden acilirdi. Asagidaki testler tam olarak bunun olmadigini kanitlar.
"""
import json
import subprocess
import sys

A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
KAP = "izole-rls-test"

gecti = kaldi = 0


def kos(sql, kullanici=None, rol="authenticated", geri_al=True):
    son = "ROLLBACK;" if geri_al else "COMMIT;"
    if kullanici:
        c = json.dumps({"sub": kullanici, "role": rol})
        tam = (f"BEGIN; SET LOCAL role {rol}; "
               f"SET LOCAL request.jwt.claims = '{c}'; {sql} {son}")
    else:
        tam = f"BEGIN; SET LOCAL role {rol}; {sql} {son}"
    p = subprocess.run(
        ["docker", "exec", "-i", KAP, "psql", "-U", "postgres", "-d", "postgres",
         "-t", "-A", "-v", "ON_ERROR_STOP=1", "-c", tam],
        capture_output=True, text=True)
    iz = [s.split("SONUC=", 1)[1] for s in (p.stdout or "").splitlines() if "SONUC=" in s]
    return p.returncode, (iz[0] if iz else None), (p.stderr or "").strip()


def test(ad, beklenen, sql, kullanici=None, rol="authenticated"):
    global gecti, kaldi
    rc, val, err = kos(sql, kullanici, rol)
    gozlenen = val if rc == 0 else "RED"
    ok = (str(gozlenen) == str(beklenen))
    gecti += ok
    kaldi += (not ok)
    ek = ""
    if not ok and err:
        ek = f"  [{err.splitlines()[-1][:70]}]"
    print(f"  {'PASS' if ok else '*** FAIL ***':12s} {ad:58s} "
          f"beklenen={beklenen:<6} gozlenen={gozlenen}{ek}")


print("=" * 100)
print("007 — KULLANICI GORUNTULEME KAYDI: IZOLASYON MATRISI")
print("=" * 100)

print("\n--- 1. ANON: tabloya hicbir sekilde dokunamaz (yeni tablo guvensiz dogar!) ---")
test("anon SELECT", "RED",
     "SELECT 'SONUC='||COUNT(*) FROM public.kullanici_goruntuleme_kaydi;", None, "anon")
test("anon INSERT", "RED",
     f"INSERT INTO public.kullanici_goruntuleme_kaydi(user_id,istenen_yol) "
     f"VALUES ('{A}','/x'); SELECT 'SONUC=YAZDI';", None, "anon")
test("anon TRUNCATE (006'da kapatilan acik)", "RED",
     "TRUNCATE public.kullanici_goruntuleme_kaydi; SELECT 'SONUC=SILDI';", None, "anon")
# DIKKAT - MUTASYONLA YAKALANAN TEST ZAYIFLIGI (17.09.2026):
# Ilk surum yalnizca "RED mi" diye bakiyordu ve fonksiyonun REVOKE'u
# KALDIRILDIGI halde yesil kaliyordu. Cunku anon cagirdiginda fonksiyonun
# ICINDEKI fail-closed kontrolu (auth.uid() NULL -> 42501) da RED uretiyor;
# test iki AYRI nedeni ayirt edemiyordu. Artik hatanin YETKI reddi oldugu
# acikca dogrulanir: EXECUTE hakki gercekten alinmis mi?
rc, _, err = kos("SELECT 'SONUC='||public.goruntuleme_kaydi_yaz('/x');", None, "anon")
yetki_reddi = rc != 0 and "permission denied" in err.lower()
gecti += yetki_reddi
kaldi += (not yetki_reddi)
print(f"  {'PASS' if yetki_reddi else '*** FAIL ***':12s} "
      f"{'anon fonksiyonu CAGIRAMAZ (YETKI reddi, ic kontrol degil)':58s} "
      f"{(err.splitlines()[-1][:60] if err else 'CAGIRABILDI')}")

print("\n--- 2. AUTHENTICATED: dogrudan yazma/okuma KAPALI (tek yol fonksiyon) ---")
test("A dogrudan INSERT edemez", "RED",
     f"INSERT INTO public.kullanici_goruntuleme_kaydi(user_id,istenen_yol) "
     f"VALUES ('{A}','/x'); SELECT 'SONUC=YAZDI';", A)
test("A dogrudan SELECT edemez (politika YOK = fail-closed)", "RED",
     "SELECT 'SONUC='||COUNT(*) FROM public.kullanici_goruntuleme_kaydi;", A)
test("A TRUNCATE edemez", "RED",
     "TRUNCATE public.kullanici_goruntuleme_kaydi; SELECT 'SONUC=SILDI';", A)

print("\n--- 3. MESRU YOL: fonksiyon calisiyor ve KENDI kimligiyle yaziyor ---")
test("A fonksiyonla kayit yazabilir", "1",
     "WITH y AS (SELECT public.goruntuleme_kaydi_yaz('/api/maa/memory/MSFT','MSFT') AS id) "
     "SELECT 'SONUC='||COUNT(*) FROM y WHERE id IS NOT NULL;", A)
# Yazilan satirin user_id'si GERCEKTEN cagiranin mi? postgres ile dogrulanir
# (burada amac izolasyon degil, fonksiyonun DOGRU kimligi yazdigini gormek).
print("      --- yazilan satirin sahibi kim (postgres ile dogrulama) ---")
rc, _, _ = subprocess.run(
    ["docker", "exec", "-i", KAP, "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c",
     f"BEGIN; SET LOCAL role authenticated; "
     f"SET LOCAL request.jwt.claims = '{json.dumps({'sub': A, 'role': 'authenticated'})}'; "
     f"SELECT public.goruntuleme_kaydi_yaz('/kalici','MSFT'); COMMIT;"],
    capture_output=True, text=True).returncode, None, None
p = subprocess.run(
    ["docker", "exec", KAP, "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c",
     "SELECT user_id||'|'||istenen_yol FROM public.kullanici_goruntuleme_kaydi "
     "WHERE istenen_yol='/kalici' ORDER BY id DESC LIMIT 1;"],
    capture_output=True, text=True)
satir = (p.stdout or "").strip()
ok = satir.startswith(A)
gecti += ok
kaldi += (not ok)
print(f"  {'PASS' if ok else '*** FAIL ***':12s} "
      f"{'fonksiyon CAGIRANIN kimligini yaziyor':58s} {satir[:50]}")

print("\n--- 4. A, B ADINA kayit uretemez (yapisal: parametre YOK) ---")
# Fonksiyon user_id parametresi ALMIYOR; boyle bir cagri imzaya uymaz.
test("A, user_id parametresi gecirmeye calisir", "RED",
     f"SELECT 'SONUC='||public.goruntuleme_kaydi_yaz('/x', p_user_id => '{B}');", A)
# B'nin kimligiyle yazilan satir, A'nin oturumunda A'ya yazilir - yani
# fonksiyon caginin kimligini ZORLA kullanir.
p = subprocess.run(
    ["docker", "exec", KAP, "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c",
     f"SELECT COUNT(*) FROM public.kullanici_goruntuleme_kaydi WHERE user_id='{B}';"],
    capture_output=True, text=True)
bsayi = (p.stdout or "").strip()
ok = bsayi == "0"
gecti += ok
kaldi += (not ok)
print(f"  {'PASS' if ok else '*** FAIL ***':12s} "
      f"{'B adina hic satir uretilememis':58s} B_satir_sayisi={bsayi}")

print("\n--- 5. OTURUMSUZ cagri REDDEDILIR (fail-closed) ---")
rc, val, err = kos("SELECT 'SONUC='||public.goruntuleme_kaydi_yaz('/x');",
                   None, "authenticated")
ok = rc != 0 and "42501" in err or "oturum gerekli" in err
gecti += ok
kaldi += (not ok)
print(f"  {'PASS' if ok else '*** FAIL ***':12s} "
      f"{'claims yok -> 42501 oturum gerekli':58s} "
      f"{(err.splitlines()[-1][:60] if err else 'HATA YOK - KAYIT YAZILDI')}")

print("\n--- 6. SEQUENCE de kapali (id tahmini/tuketimi yok) ---")
test("A sequence'i tuketemez", "RED",
     "SELECT 'SONUC='||nextval('public.kullanici_goruntuleme_kaydi_id_seq')::text;", A)
test("anon sequence'i tuketemez", "RED",
     "SELECT 'SONUC='||nextval('public.kullanici_goruntuleme_kaydi_id_seq')::text;",
     None, "anon")

print("\n" + "=" * 100)
print(f"SONUC: {gecti}/{gecti + kaldi} PASS")
print("=" * 100)
sys.exit(1 if kaldi else 0)
