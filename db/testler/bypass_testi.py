"""RLS'in KAPSAMADIGI yollar. PostgreSQL'de RLS; TRUNCATE'i kapsamaz."""
import subprocess, json
A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

def kos(sql, kullanici=None, rol="authenticated", geri_al=True):
    son = "ROLLBACK;" if geri_al else "COMMIT;"
    if kullanici:
        c = json.dumps({"sub": kullanici, "role": rol})
        tam = f"BEGIN; SET LOCAL role {rol}; SET LOCAL request.jwt.claims = '{c}'; {sql} {son}"
    else:
        tam = f"BEGIN; SET LOCAL role {rol}; {sql} {son}"
    p = subprocess.run(["docker","exec","-i","izole-rls-test","psql","-U","postgres",
        "-d","postgres","-t","-A","-v","ON_ERROR_STOP=1","-c",tam],
        capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

print("="*100); print("RLS'IN KAPSAMADIGI ERISIM YOLLARI"); print("="*100)

print("\n--- BULGU ADAYI 1: TRUNCATE (RLS TRUNCATE'i KAPSAMAZ) ---")
for rol, kim in (("authenticated", A), ("anon", None)):
    rc, out, err = kos("TRUNCATE public.profiles;", kim, rol)
    if rc == 0:
        print(f"  *** KRITIK *** {rol:14s} TRUNCATE public.profiles -> BASARILI (TUM PROFILLER SILINEBILIR)")
    else:
        print(f"  guvenli      {rol:14s} TRUNCATE public.profiles -> RED ({err.splitlines()[-1][:55] if err else '?'})")
    rc, out, err = kos("TRUNCATE public.user_portfolios;", kim, rol)
    if rc == 0:
        print(f"  *** KRITIK *** {rol:14s} TRUNCATE user_portfolios -> BASARILI (TUM PORTFOYLER SILINEBILIR)")
    else:
        print(f"  guvenli      {rol:14s} TRUNCATE user_portfolios -> RED ({err.splitlines()[-1][:55] if err else '?'})")

print("\n--- BULGU ADAYI 2: ROL YUKSELTME (A kendi role'unu admin yapabilir mi) ---")
rc, out, err = kos(f"UPDATE public.profiles SET role='admin' WHERE id='{A}'; "
                   f"SELECT 'SONUC='||role::text FROM public.profiles WHERE id='{A}';", A)
if rc == 0 and "SONUC=admin" in out:
    print("  *** BULGU ***  A KENDI role'unu 'admin' yapabildi (gizil ayricalik yukseltme)")
else:
    print(f"  guvenli      rol yukseltme RED/engellendi ({err.splitlines()[-1][:55] if err else out[:40]})")

print("\n--- BULGU ADAYI 3: A, B'nin role'unu degistirebilir mi ---")
rc, out, err = kos(f"WITH u AS (UPDATE public.profiles SET role='admin' WHERE id='{B}' RETURNING 1) "
                   f"SELECT 'SONUC='||COUNT(*) FROM u;", A)
iz = [s.split("SONUC=")[1] for s in out.splitlines() if "SONUC=" in s]
# DIKKAT: rc != 0 "olculemedi" DEGIL, DAHA GUCLU bir engeldir - ifade yetki
# katmaninda reddedildi, RLS'in satir filtresine hic ulasmadi. Ilk surumde
# bu durum '?' olarak okunup yanlislikla BULGU sayiliyordu.
if rc != 0:
    print(f"  guvenli      A -> B'nin role'u: YETKI katmaninda RED ({err.splitlines()[-1][:55] if err else '?'})")
elif iz and iz[0] == "0":
    print("  guvenli      A -> B'nin role'u: etkilenen satir = 0 (RLS satir filtresi)")
else:
    print(f"  *** BULGU ***  A -> B'nin role'u: etkilenen satir = {iz[0] if iz else '?'}")

# ---------------------------------------------------------------------
# OLUMLU DENETIM (Y6 geri uyumluluk): engel FAZLA genis olmamali.
# Kolon yetkisi daraltmasi mesru guncellemeyi de kesiyorsa bu bir REGRESYON'dur;
# "her sey reddedildi" bir basari degil, kullanicinin profilini duzenleyememesidir.
# ---------------------------------------------------------------------
print("\n--- OLUMLU DENETIM: mesru guncelleme HALA calisiyor mu ---")
for etiket, sql, beklenen in (
    ("A kendi full_name'ini degistirir",
     f"WITH u AS (UPDATE public.profiles SET full_name='Yeni Ad' WHERE id='{A}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", "1"),
    ("A kendi company_name'ini degistirir",
     f"WITH u AS (UPDATE public.profiles SET company_name='Yeni Sirket' WHERE id='{A}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", "1"),
    ("A kendi portfoyunu adlandirir",
     f"WITH u AS (UPDATE public.user_portfolios SET portfolio_name='Yeni' WHERE user_id='{A}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", "1"),
):
    rc, out, err = kos(sql, A)
    iz = [s.split("SONUC=")[1] for s in out.splitlines() if "SONUC=" in s]
    gozlenen = iz[0] if (rc == 0 and iz) else f"RED:{err.splitlines()[-1][:40] if err else rc}"
    print(f"  {'gecti  ' if gozlenen == beklenen else '*** REGRESYON ***'}  {etiket}: {gozlenen} (beklenen {beklenen})")

print("\n--- EK DENETIM: id kolonu da kilitli mi (satir sahipligi calinamaz) ---")
rc, out, err = kos(f"UPDATE public.profiles SET id='{B}' WHERE id='{A}';", A)
print(f"  {'guvenli' if rc != 0 else '*** BULGU ***'}      A kendi id'sini B yapamaz -> "
      f"{(err.splitlines()[-1][:55] if err else 'IZIN VERILDI')}")

print("\n--- BULGU ADAYI 4: SECURITY DEFINER fonksiyonlar (RLS atlayabilir) ---")
rc, out, err = kos("SELECT 'SONUC='||COUNT(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                   "WHERE n.nspname='public' AND p.prosecdef;", None, "anon")
iz = [s.split("SONUC=")[1] for s in out.splitlines() if "SONUC=" in s]
print(f"  public semada SECURITY DEFINER fonksiyon sayisi: {iz[0] if iz else '?'}")
