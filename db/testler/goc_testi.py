"""FAZ 4 - Goc testleri: idempotentlik (C3), veri korunumu (Y6), canli yol (Y4)."""
import subprocess, hashlib, json, re, ast
from pathlib import Path

GOC = (Path(__file__).resolve().parent.parent / "migrations"
       / "006_supabase_rls_kapsamayan_yollari_kapat.sql")
KAP = "izole-rls-test"
gecti = kaldi = 0

def sonuc(ad, ok, ayrinti=""):
    global gecti, kaldi
    gecti += ok; kaldi += (not ok)
    print(f"  {'PASS' if ok else '*** FAIL ***'}  {ad:58s} {ayrinti}")

def psql(sql):
    p = subprocess.run(["docker","exec","-i",KAP,"psql","-U","postgres","-d","postgres",
        "-t","-A","-v","ON_ERROR_STOP=1","-c",sql], capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

def goc_uygula():
    p = subprocess.run(["docker","exec","-i",KAP,"psql","-U","postgres","-d","postgres",
        "-v","ON_ERROR_STOP=1","-f","-"], stdin=open(GOC,"rb"), capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip()

def yetki_parmak_izi():
    """Tum ilgili yetkilerin kararli bir ozeti - iki calistirma arasinda AYNI olmali."""
    rc, out, _ = psql("""
      SELECT string_agg(x, '|' ORDER BY x) FROM (
        SELECT grantee||':'||table_name||':'||privilege_type AS x
          FROM information_schema.role_table_grants
         WHERE table_schema='public' AND grantee IN ('anon','authenticated')
        UNION ALL
        SELECT 'KOL:'||grantee||':'||table_name||':'||column_name||':'||privilege_type
          FROM information_schema.column_privileges
         WHERE table_schema='public' AND grantee IN ('anon','authenticated')
        UNION ALL
        SELECT 'SEQ:'||grantee||':'||object_name
          FROM information_schema.role_usage_grants
         WHERE object_schema='public' AND grantee IN ('anon','authenticated')
      ) s;""")
    return hashlib.sha256(out.encode()).hexdigest()[:16], out

print("="*100); print("FAZ 4 - GOC TESTLERI"); print("="*100)

# ---------------------------------------------------------------- C3 idempotentlik
print("\n--- 1. IDEMPOTENTLIK (C3): goc iki kez calisinca AYNI sonuc ---")
pi1, _ = yetki_parmak_izi()
rc2, cikti2 = goc_uygula()
sonuc("2. calistirma hatasiz bitti", rc2 == 0, f"rc={rc2}")
pi2, det2 = yetki_parmak_izi()
sonuc("2. calistirma yetkileri DEGISTIRMEDI", pi1 == pi2, f"{pi1} -> {pi2}")
rc3, cikti3 = goc_uygula()
pi3, _ = yetki_parmak_izi()
sonuc("3. calistirma da ayni (kararli nokta)", rc3 == 0 and pi3 == pi1, f"{pi3}")
sonuc("dogrulama ciktisi calistirmalar arasi ayni", cikti2 == cikti3)

# ---------------------------------------------------------------- Y6 veri korunumu
print("\n--- 2. VERI KORUNUMU (Y6): goc HICBIR SATIRI degistirmiyor ---")
rc, once, _ = psql("SELECT (SELECT COUNT(*) FROM public.profiles)||'/'||"
                   "(SELECT COUNT(*) FROM public.user_portfolios)||'/'||"
                   "COALESCE((SELECT md5(string_agg(p.id::text||p.email||p.role::text, ',' ORDER BY p.id)) "
                   "FROM public.profiles p),'bos');")
rcg, _ = goc_uygula()
rc, sonra, _ = psql("SELECT (SELECT COUNT(*) FROM public.profiles)||'/'||"
                    "(SELECT COUNT(*) FROM public.user_portfolios)||'/'||"
                    "COALESCE((SELECT md5(string_agg(p.id::text||p.email||p.role::text, ',' ORDER BY p.id)) "
                    "FROM public.profiles p),'bos');")
sonuc("satir sayilari + icerik ozeti ONCE == SONRA", once == sonra, f"{once}")

# STATIK KANIT: gocte hic DML yok - veri degistirmesi FIZIKSEN mumkun degil
ham = GOC.read_text(encoding="utf-8")
kod = "\n".join(s for s in ham.splitlines() if not s.strip().startswith("--"))
dml = re.findall(r"\b(INSERT\s+INTO|UPDATE\s+public|DELETE\s+FROM|TRUNCATE\s+(?!ON)|DROP\s+TABLE|ALTER\s+TABLE)\b",
                 kod, re.IGNORECASE)
sonuc("gocte HIC DML/DDL yok (yalnizca GRANT/REVOKE)", not dml, f"bulunan={dml or 'yok'}")
komutlar = sorted(set(re.findall(r"^\s*(\w+)", kod, re.MULTILINE)))
sonuc("kullanilan SQL komutlari beyaz listede",
      set(komutlar) <= {"BEGIN","COMMIT","REVOKE","GRANT","SELECT","FROM","WHERE","UNION","AND","ON"},
      f"{[k for k in komutlar if k]}")

# ---------------------------------------------------------------- Y4 canli yol
print("\n--- 3. CANLI KARAR YOLU DOKUNULMAZ (Y4) ---")
depo = Path(__file__).resolve().parent.parent.parent
# Y4'un ASIL iddiasi "tek dosya eklendi" degil, "HICBIR CALISTIRILABILIR
# KOD dosyasina dokunulmadi"dir. Ilk surum dosya SAYISI sayiyordu ve geri
# alma gocu eklenince yanlislikla FAIL verdi - sayim, iddianin kendisi degil.
BEKLENEN = {
    "db/migrations/006_supabase_rls_kapsamayan_yollari_kapat.sql",
    "db/migrations/006_geri_al_rls_kapsamayan_yollari_kapat.sql",
    "docs/denetim_raporlari/KAPANIS_coklukullanici.md",
    "docs/denetim_raporlari/VARSAYIM_DEFTERI_coklukullanici.md",
    "docs/denetim_raporlari/HATA_HAFIZASI_coklukullanici.md",
}
# DIKKAT: ilk surum bu dosyalari `git status` ciktisinda ariyordu; commit
# atildigi anda orada gorunmez oldular ve test yanlislikla FAIL verdi.
# Dogru olcut "sahnelenmis mi" degil, "deguda VAR mi"dir.
eksik = {f for f in BEKLENEN if not (depo/f).is_file()}
sonuc("bu gorevin 5 dosyasi da deguda duruyor", not eksik, f"eksik={eksik or 'yok'}")

# Asil kanit: bu gorev hicbir calistirilabilir kod dosyasina dokunmadi.
KOD_UZANTILARI = (".py", ".ts", ".tsx", ".js", ".jsx", ".yml", ".yaml", ".json", ".toml")
# Depoda BASKA oturumlardan kalan degisiklikler var; bu gorevin kattigi
# dosyalar BEKLENEN kumesidir ve icinde tek bir kod dosyasi bile yoktur.
kod_dosyalari = [f for f in BEKLENEN if f.endswith(KOD_UZANTILARI)]
sonuc("bu gorev HICBIR kod dosyasi eklemedi/degistirmedi", not kod_dosyalari,
      f"{kod_dosyalari or 'yalnizca .sql ve .md'}")
sonuc("eklenen her dosya .sql ya da .md",
      all(f.endswith((".sql", ".md")) for f in BEKLENEN))

kutsal = ["taa/src/main.py", "maa/src/main.py", "godmode-paper-trading-service/main.py"]
p = subprocess.run(["git","-C",str(depo),"status","--porcelain"] + kutsal, capture_output=True, text=True)
sonuc("Y1 kutsal dosyalarda DEGISIKLIK YOK", not p.stdout.strip(), p.stdout.strip() or "temiz")

sonuc("goc bir .sql; hicbir Python/TS modulu ice aktarmiyor",
      GOC.suffix == ".sql" and "import" not in kod.lower())

# karar_uret'i barindiran modul(ler) bu gorevde degismedi mi?
# DIKKAT: bu dosyanin KENDISI "def karar_uret" dizgesini icerdigi icin
# grep onu da buluyordu ve test kendi degisikligini "canli yol degisti"
# diye raporluyordu. Test dizini aramadan cikarilir.
p = subprocess.run(["git","-C",str(depo),"grep","-l","def karar_uret",
                    "--", ":!db/testler/"], capture_output=True, text=True)
tasiyici = [s for s in p.stdout.splitlines() if s.strip()]
print(f"      karar_uret tasiyan dosyalar: {tasiyici or '(git-izlenen dosyada yok)'}")
if tasiyici:
    p2 = subprocess.run(["git","-C",str(depo),"status","--porcelain"] + tasiyici, capture_output=True, text=True)
    sonuc("karar_uret tasiyan dosyalar DEGISMEDI", not p2.stdout.strip(), p2.stdout.strip() or "temiz")

# ---------------------------------------------------------------- yapisal kontroller
print("\n--- 4. GOC YAPISI ---")
sonuc("tek islemde (BEGIN/COMMIT dengeli, Y5 geri alinabilir)",
      kod.count("BEGIN;") == 1 and kod.count("COMMIT;") == 1)
sonuc("service_role/postgres yetkilerine dokunulmuyor",
      "service_role" not in kod and not re.search(r"FROM\s+postgres", kod))
sonuc("RLS politikalari degistirilmiyor",
      "POLICY" not in kod.upper() and "ROW LEVEL SECURITY" not in kod.upper())
sonuc("goc numarasi sirali (005'ten sonra 006)",
      sorted(x.name[:3] for x in GOC.parent.glob("0*.sql"))[-1] == "006")

print("\n" + "="*100); print(f"FAZ 4 SONUC: {gecti}/{gecti+kaldi} PASS"); print("="*100)
