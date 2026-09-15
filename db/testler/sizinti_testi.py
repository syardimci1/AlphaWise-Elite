"""FAZ 3 — Sizinti matrisi. GERCEK kullanici rolu ile (superuser DEGIL)."""
import subprocess, json, sys

A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
C = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"   # yetim: ne A ne B

def kos(sql, kullanici=None, rol="authenticated"):
    """SQL'i belirtilen kullanici kimligiyle calistirir. kullanici=None -> anon."""
    # ROLLBACK: testler izole ortamin durumunu BOZMAZ, tekrarlanabilir kalir.
    if kullanici:
        claims = json.dumps({"sub": kullanici, "role": rol})
        tam = (f"BEGIN; SET LOCAL role {rol}; "
               f"SET LOCAL request.jwt.claims = '{claims}'; {sql} ROLLBACK;")
    else:
        tam = f"BEGIN; SET LOCAL role {rol}; {sql} ROLLBACK;"
    p = subprocess.run(
        ["docker","exec","-i","izole-rls-test","psql","-U","postgres","-d","postgres",
         "-t","-A","-v","ON_ERROR_STOP=1","-c",tam],
        capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

sonuclar = []
def test(ad, beklenen, sql, kullanici, rol="authenticated"):
    rc, out, err = kos(sql, kullanici, rol)
    if rc != 0:
        gozlenen = f"RED (hata: {err.splitlines()[-1][:60] if err else '?'})"
        gecti = (beklenen == "RED")
    else:
        # SENTINEL ile ayikla: psql komut etiketleri (BEGIN/SET/COMMIT/ROLLBACK)
        # sonuc SANILMASIN. Ilk surumde tam bu hata yasandi: son satir
        # "COMMIT" idi ve 19 test yanlislikla FAIL gorundu.
        iz = [s.split("SONUC=",1)[1] for s in out.splitlines() if "SONUC=" in s]
        gozlenen = iz[0] if iz else f"<sentinel yok: {out.splitlines()[-1][:30] if out else 'bos'}>"
        gecti = (str(gozlenen) == str(beklenen))
    sonuclar.append((ad, beklenen, gozlenen, gecti))
    isaret = "PASS" if gecti else "*** FAIL ***"
    print(f"  {isaret:12s} {ad:52s} beklenen={beklenen:<6} gozlenen={gozlenen}")

print("="*100)
print("SIZINTI MATRISI — her tablo x her yon x her erisim yolu")
print("="*100)

print("\n--- 1. SELECT: A, B'nin verisini gorebilir mi? (0 gormeli) ---")
test("profiles: A -> B'nin profili", "0", f"SELECT 'SONUC='||COUNT(*) FROM public.profiles WHERE id='{B}';", A)
test("profiles: B -> A'nin profili", "0", f"SELECT 'SONUC='||COUNT(*) FROM public.profiles WHERE id='{A}';", B)
test("user_portfolios: A -> B'nin portfoyu", "0", f"SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios WHERE user_id='{B}';", A)
test("user_portfolios: B -> A'nin portfoyu", "0", f"SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios WHERE user_id='{A}';", B)

print("\n--- 2. SELECT (filtresiz): kac satir gorunuyor? (yalniz kendi = 1) ---")
test("profiles: A filtresiz SELECT *", "1", "SELECT 'SONUC='||COUNT(*) FROM public.profiles;", A)
test("profiles: B filtresiz SELECT *", "1", "SELECT 'SONUC='||COUNT(*) FROM public.profiles;", B)
test("user_portfolios: A filtresiz", "1", "SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios;", A)
test("user_portfolios: B filtresiz", "1", "SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios;", B)

print("\n--- 3. UPDATE: A, B'nin satirini degistirebilir mi? (0 etkilenmeli) ---")
test("profiles: A -> B'yi UPDATE", "0", f"WITH u AS (UPDATE public.profiles SET full_name='HACKED' WHERE id='{B}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", A)
test("user_portfolios: A -> B'yi UPDATE", "0", f"WITH u AS (UPDATE public.user_portfolios SET tickers=ARRAY['HACK'] WHERE user_id='{B}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", A)
test("user_portfolios: B -> A'yi UPDATE", "0", f"WITH u AS (UPDATE public.user_portfolios SET tickers=ARRAY['HACK'] WHERE user_id='{A}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", B)

# 006 SONRASI NOT: `profiles` uzerinde authenticated'in DELETE YETKISI de alindi.
# Beklenti "0"dan "RED"e cikti - engel artik iki katmanli: once yetki, sonra
# (politika olmadigi icin) RLS. `user_portfolios`'ta DELETE politikasi VAR ve
# yetki duruyor, orada dogru beklenti hala "0 satir etkilendi".
print("\n--- 4. DELETE: A, B'nin satirini silebilir mi? (0 etkilenmeli) ---")
test("user_portfolios: A -> B'yi DELETE", "0", f"WITH d AS (DELETE FROM public.user_portfolios WHERE user_id='{B}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM d;", A)
test("profiles: A -> B'yi DELETE (yetki+politika YOK)", "RED", f"WITH d AS (DELETE FROM public.profiles WHERE id='{B}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM d;", A)
test("profiles: A -> KENDI profilini DELETE (yetki+politika YOK)", "RED", f"WITH d AS (DELETE FROM public.profiles WHERE id='{A}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM d;", A)

print("\n--- 5. INSERT: A, B adina satir yazabilir mi? (RED olmali) ---")
test("user_portfolios: A -> B adina INSERT", "RED", f"INSERT INTO public.user_portfolios (user_id, portfolio_name, tickers) VALUES ('{B}','sahte',ARRAY['X']);", A)
test("profiles: A -> B adina INSERT", "RED", f"INSERT INTO public.profiles (id, email) VALUES ('{B}','sahte@x');", A)

print("\n--- 6. FAIL-CLOSED (C5): yetim satir (C) hic kimseye gorunmemeli ---")
test("user_portfolios: A -> C'nin (yetim) satiri", "0", f"SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios WHERE user_id='{C}';", A)
test("user_portfolios: B -> C'nin (yetim) satiri", "0", f"SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios WHERE user_id='{C}';", B)

print("\n--- 7. ANON (oturumsuz): hicbir sey gormemeli ---")
# BEKLENTI 006 ILE DEGISTI: onceden "0" idi (RLS sifir satir donduruyordu).
# 006 sonrasi anon'un SELECT YETKISI de yok, yani engel artik RLS'ten ONCE,
# yetki katmaninda devreye giriyor. "RED", "0"dan DAHA GUCLU bir sonuctur:
# RLS bir gun yanlislikla kapatilsa bile oturumsuz okuma yine reddedilir.
test("profiles: anon SELECT (yetki katmani)", "RED", "SELECT 'SONUC='||COUNT(*) FROM public.profiles;", None, "anon")
test("user_portfolios: anon SELECT (yetki katmani)", "RED", "SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios;", None, "anon")
test("profiles: anon INSERT", "RED", "INSERT INTO public.profiles(id,email) VALUES ('dddddddd-dddd-4ddd-8ddd-dddddddddddd','x@y.z'); SELECT 'SONUC=YAZDI';", None, "anon")
test("user_portfolios: anon INSERT", "RED", f"INSERT INTO public.user_portfolios(user_id,portfolio_name) VALUES ('{A}','sizinti'); SELECT 'SONUC=YAZDI';", None, "anon")
test("profiles: anon TRUNCATE (RLS kapsamaz)", "RED", "TRUNCATE public.profiles; SELECT 'SONUC=SILDI';", None, "anon")
test("user_portfolios: anon TRUNCATE (RLS kapsamaz)", "RED", "TRUNCATE public.user_portfolios; SELECT 'SONUC=SILDI';", None, "anon")
test("profiles: A kendi role'unu admin yapamaz", "RED", f"UPDATE public.profiles SET role='admin' WHERE id='{A}'; SELECT 'SONUC=YUKSELDI';", A)
test("profiles: A kendi id'sini calamaz", "RED", f"UPDATE public.profiles SET id='{B}' WHERE id='{A}'; SELECT 'SONUC=CALDI';", A)

# OLUMLU DENETIM: engeller FAZLA genis olmamali (Y6) - bunlar CALISMALI.
test("OLUMLU: A kendi full_name'ini degistirir", "1",
     f"WITH u AS (UPDATE public.profiles SET full_name='Ad' WHERE id='{A}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", A)
# NOT: `tickers` NOT NULL - ilk surumde verilmemis ve test kendi hatasiyla
# RED almisti. Guvenlik bulgusu DEGILDI; testin girdisi eksikti.
test("OLUMLU: A kendi portfoyunu ekler", "1",
     f"WITH u AS (INSERT INTO public.user_portfolios(user_id,portfolio_name,tickers) VALUES ('{A}','Yeni',ARRAY['NVDA']) RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", A)
test("OLUMLU: A kendi portfoyunu siler", "1",
     f"WITH u AS (DELETE FROM public.user_portfolios WHERE user_id='{A}' RETURNING 1) SELECT 'SONUC='||COUNT(*) FROM u;", A)

print("\n--- 8. JWT'siz authenticated (claims yok): gormemeli ---")
test("profiles: claims'siz authenticated", "0", "SELECT 'SONUC='||COUNT(*) FROM public.profiles;", None, "authenticated")

print("\n" + "="*100)
gecen = sum(1 for *_, g in sonuclar if g)
print(f"SONUC: {gecen}/{len(sonuclar)} PASS")
kalanlar = [a for a,_,_,g in sonuclar if not g]
if kalanlar:
    print("*** BASARISIZ TESTLER ***")
    for k in kalanlar: print("   -", k)
sys.exit(0 if gecen == len(sonuclar) else 1)
