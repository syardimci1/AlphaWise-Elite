"""Faz 3.5 - RLS'in ATLANABILECEGI diger yollar. Her biri DENENIR, varsayilmaz."""
import subprocess, json
A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

def kos(sql, kullanici=None, rol="authenticated"):
    if kullanici:
        c = json.dumps({"sub": kullanici, "role": rol})
        tam = f"BEGIN; SET LOCAL role {rol}; SET LOCAL request.jwt.claims = '{c}'; {sql} ROLLBACK;"
    else:
        tam = f"BEGIN; SET LOCAL role {rol}; {sql} ROLLBACK;"
    p = subprocess.run(["docker","exec","-i","izole-rls-test","psql","-U","postgres",
        "-d","postgres","-t","-A","-v","ON_ERROR_STOP=1","-c",tam],
        capture_output=True, text=True)
    iz = [s.split("SONUC=")[1] for s in (p.stdout or "").splitlines() if "SONUC=" in s]
    return p.returncode, (iz[0] if iz else None), (p.stderr or "").strip()

gecti = kaldi = 0
def dene(ad, sql, beklenen, kullanici=A, rol="authenticated"):
    global gecti, kaldi
    rc, val, err = kos(sql, kullanici, rol)
    gozlenen = val if rc == 0 else f"RED"
    ok = (gozlenen == beklenen)
    gecti += ok; kaldi += (not ok)
    ek = "" if ok or not err else f"  [{err.splitlines()[-1][:60]}]"
    print(f"  {'PASS' if ok else '*** FAIL ***'}  {ad:52s} beklenen={beklenen:6s} gozlenen={gozlenen}{ek}")

print("="*100)
print("FAZ 3.5 - RLS'IN KAPSAMADIGI/ATLANABILECEGI DIGER YOLLAR")
print("="*100)

print("\n--- A) JOIN yolu: iki tabloyu birlestirerek baskasinin verisi sizar mi? ---")
dene("A: profiles JOIN user_portfolios (tum evren)",
     "SELECT 'SONUC='||COUNT(*) FROM public.profiles p JOIN public.user_portfolios u ON u.user_id=p.id;", "1")
dene("A: B'nin id'siyle acikca JOIN",
     f"SELECT 'SONUC='||COUNT(*) FROM public.profiles p JOIN public.user_portfolios u ON u.user_id=p.id WHERE p.id='{B}';", "0")
dene("A: alt-sorgu ile B'nin e-postasi",
     f"SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios u WHERE u.user_id IN (SELECT id FROM public.profiles WHERE id='{B}');", "0")
dene("A: LEFT JOIN ile B'nin varligi sizar mi",
     f"SELECT 'SONUC='||COUNT(*) FROM public.user_portfolios u LEFT JOIN public.profiles p ON p.id=u.user_id WHERE u.user_id='{B}';", "0")

print("\n--- B) TOPLAM/VARLIK sizintisi: satir gorunmese de sayisi/varligi ogrenilebilir mi? ---")
dene("A: profiles toplam satir sayisi (evrenin buyuklugu)",
     "SELECT 'SONUC='||COUNT(*) FROM public.profiles;", "1")
dene("A: EXISTS ile B'nin varligi",
     f"SELECT 'SONUC='||(EXISTS(SELECT 1 FROM public.profiles WHERE id='{B}'))::int;", "0")
dene("A: B'nin e-postasi MAX ile sizar mi",
     f"SELECT 'SONUC='||COALESCE(MAX(email),'YOK') FROM public.profiles WHERE id='{B}';", "YOK")

print("\n--- C) SECURITY DEFINER fonksiyon dogrudan cagrilabilir mi? ---")
for rol, kim in (("authenticated", A), ("anon", None)):
    rc, val, err = kos("SELECT 'SONUC='||public.yeni_kullanici_profili_olustur()::text;", kim, rol)
    son = err.splitlines()[-1][:70] if err else f"CAGRILDI:{val}"
    print(f"  {'PASS' if rc != 0 else '*** FAIL ***'}  {rol:14s} dogrudan cagri -> {'RED' if rc else 'BASARILI'}  [{son}]")
    gecti += (rc != 0); kaldi += (rc == 0)

print("\n--- D) SEQUENCE: anon/authenticated id tuketebilir/ogrenebilir mi? ---")
# 006 sonrasi: anon RED olmali (INSERT yetkisi yok, sequence'e ihtiyaci yok),
# authenticated ise BASARILI kalmali (serial varsayilani icin gerekli - Y6).
for rol, kim, beklenen in (("authenticated", A, "BASARILI"), ("anon", None, "RED")):
    rc, val, err = kos("SELECT 'SONUC='||nextval('public.user_portfolios_id_seq')::text;", kim, rol)
    gozlenen = "BASARILI" if rc == 0 else "RED"
    ok = gozlenen == beklenen
    gecti += ok; kaldi += (not ok)
    print(f"  {'PASS' if ok else '*** FAIL ***'}  {rol:14s} nextval() -> {gozlenen:9s} (beklenen {beklenen})")

print("\n--- E) SEMA YAZMA: kullanici kendi tablosunu/fonksiyonunu yaratabilir mi? ---")
for rol, kim in (("authenticated", A), ("anon", None)):
    rc, val, err = kos("CREATE TABLE public.sizinti_deneme(x int); SELECT 'SONUC=YARATILDI';", kim, rol)
    print(f"  {'*** BULGU ***' if rc == 0 else 'guvenli     '}  {rol:14s} public semada CREATE TABLE -> {'BASARILI' if rc==0 else 'RED'}")

print("\n--- F) SISTEM KATALOGU: baska kullanicilarin kimligi katalogdan okunabilir mi? ---")
dene("A: auth.users dogrudan okunabilir mi", "SELECT 'SONUC='||COUNT(*) FROM auth.users;", "RED")
rc, val, err = kos("SELECT 'SONUC='||COUNT(*) FROM pg_authid;", A)
print(f"  {'PASS' if rc != 0 else '*** FAIL ***'}  A: pg_authid (parola karmalari) -> {'RED' if rc else 'OKUNDU:'+str(val)}")
gecti += (rc != 0); kaldi += (rc == 0)

print("\n" + "="*100)
print(f"SONUC: {gecti}/{gecti+kaldi} PASS")
print("="*100)
