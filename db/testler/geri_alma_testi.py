"""FAZ 5 - Geri alma gocu GIDIS-DONUS testi (Y5)."""
import subprocess, hashlib
from pathlib import Path
G = Path(__file__).resolve().parent.parent / "migrations"
ILERI = G/"006_supabase_rls_kapsamayan_yollari_kapat.sql"
GERI  = G/"006_geri_al_rls_kapsamayan_yollari_kapat.sql"
gecti = kaldi = 0

def sonuc(ad, ok, ek=""):
    global gecti, kaldi
    gecti += ok; kaldi += (not ok)
    print(f"  {'PASS' if ok else '*** FAIL ***'}  {ad:56s} {ek}")

def uygula(dosya, kap="izole-rls-test"):
    p = subprocess.run(["docker","exec","-i",kap,"psql","-U","postgres","-d","postgres",
        "-v","ON_ERROR_STOP=1","-f","-"], stdin=open(dosya,"rb"), capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

# DIKKAT - ILK SURUMDEKI GECERSIZ KARSILASTIRMA:
# relacl bir DIZIDIR ve elemanlarinin sirasi, yetkilerin VERILIS SIRASINI
# yansitir. Uretimde {postgres,anon,authenticated,service_role}, geri alma
# sonrasi {postgres,authenticated,service_role,anon} cikti - KUME AYNI, SIRA
# farkli. relacl::text'i dizge olarak kiyaslamak bu yuzden gecersiz bir
# esitlik testidir ve saglam bir geri almayi "BOZUK" gosterir.
# Dogrusu: aclexplode() ile satirlara acip SIRALI bir kume uretmek.
ACL_SORGU = """SELECT string_agg(x,'|' ORDER BY x) FROM (
  SELECT c.relname||':'||a.grantee::regrole::text||':'||a.privilege_type AS x
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace,
         LATERAL aclexplode(c.relacl) a
   WHERE n.nspname='public' AND c.relname IN ('profiles','user_portfolios','user_portfolios_id_seq')
  UNION ALL
  SELECT 'KOL:'||grantee||':'||table_name||':'||column_name||':'||privilege_type
    FROM information_schema.column_privileges
   WHERE table_schema='public' AND grantee IN ('anon','authenticated')
) s;"""

def acl(kap="izole-rls-test"):
    p = subprocess.run(["docker","exec","-i",kap,"psql","-U","postgres","-d","postgres",
        "-t","-A","-c",ACL_SORGU], capture_output=True, text=True)
    ham = (p.stdout or "").strip()
    return hashlib.sha256(ham.encode()).hexdigest()[:16], ham

print("="*100); print("FAZ 5 - GERI ALMA GOCU GIDIS-DONUS TESTI"); print("="*100)

URETIM, uretim_ham = acl("supabase-db")
print(f"\n  URETIM parmak izi (dokunulmadi, salt okuma): {URETIM}")

# --- su an 006 UYGULANMIS durumda ---
KAPALI, _ = acl()
sonuc("006 uygulanmis durum URETIMDEN FARKLI (goc gercekten is yapiyor)", KAPALI != URETIM,
      f"{KAPALI} != {URETIM}")

print("\n--- 1. GERI ALMA: uretim durumuna donuyor mu? ---")
rc, out, err = uygula(GERI)
sonuc("geri alma hatasiz calisti", rc == 0, err.splitlines()[-1][:60] if err else "")
GERI_ALINMIS, geri_ham = acl()
sonuc("geri alma sonrasi ACL == URETIM ACL (BIREBIR)", GERI_ALINMIS == URETIM,
      f"{GERI_ALINMIS} vs {URETIM}")
if GERI_ALINMIS != URETIM:
    a = set(uretim_ham.split("|")); b = set(geri_ham.split("|"))
    print(f"      URETIMDE olup gerialmada YOK : {sorted(a-b)[:6]}")
    print(f"      GERIALMADA olup uretimde YOK : {sorted(b-a)[:6]}")

print("\n--- 2. GERI ALMA IDEMPOTENT MI ---")
rc2, _, _ = uygula(GERI)
G2, _ = acl()
sonuc("ikinci kez calisinca ayni", rc2 == 0 and G2 == GERI_ALINMIS, G2)

print("\n--- 3. TAM TUR: ileri -> geri -> ileri -> geri kararli mi ---")
uygula(ILERI); I1, _ = acl()
uygula(GERI);  G1, _ = acl()
uygula(ILERI); I2, _ = acl()
uygula(GERI);  G3, _ = acl()
sonuc("her 'ileri' ayni sonucu veriyor", I1 == I2 == KAPALI, f"{I1} / {I2}")
sonuc("her 'geri' ayni sonucu veriyor", G1 == G3 == URETIM, f"{G1} / {G3}")

print("\n--- 4. GERI ALMA GERCEKTEN ACIKLARI GERI ACIYOR MU (durusun anlamli oldugunun kaniti) ---")
p = subprocess.run(["docker","exec","-i","izole-rls-test","psql","-U","postgres","-d","postgres",
    "-t","-A","-c","BEGIN; SET LOCAL role anon; TRUNCATE public.profiles; ROLLBACK;"],
    capture_output=True, text=True)
sonuc("geri alma sonrasi anon TRUNCATE yeniden MUMKUN (beklenen)", p.returncode == 0,
      "acik yeniden acildi - dosyadaki UYARI dogru")

print("\n--- 5. ILERI GOCU TEKRAR UYGULA (ortami korumali durumda birak) ---")
rc, out, _ = uygula(ILERI)
SON, _ = acl()
sonuc("ortam yeniden KORUMALI durumda", rc == 0 and SON == KAPALI, SON)

print("\n" + "="*100); print(f"FAZ 5 SONUC: {gecti}/{gecti+kaldi} PASS"); print("="*100)
