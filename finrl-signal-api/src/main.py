"""
ALPHAWISE - FinRL-X Canli Sinyal API
deploy.sh'nin dogrulanmis "single" modunu HTTP'ye sarmalar.
deploy.sh'ye hic dokunmuyor, sadece cagirip sonucu okuyor.
"""
import subprocess
from datetime import date
from fastapi import FastAPI, HTTPException

app = FastAPI(title="ALPHAWISE - FinRL-X Signal API")

FINRL_DIR = "/opt/alphawise/commercial/AlphaWise-Elite/finrl-x"


@app.get("/health")
def health():
    return {"service": "FinRL-X Signal API", "status": "ok"}


@app.get("/signal/{strategy}")
def get_signal(strategy: str, target_date: str = None):
    """
    Verilen strateji icin bugunun (ya da belirtilen tarihin) sinyalini uretir.
    deploy.sh --mode single'i cagirir, sadece sinyal - GERCEK ISLEM YAPMAZ.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    cmd = [
        "docker", "compose", "run", "--rm", "finrl-trading",
        "./deploy.sh", "--strategy", strategy, "--mode", "single", "--date", target_date,
    ]

    try:
        result = subprocess.run(
            cmd, cwd=FINRL_DIR, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Strateji calistirma zaman asimina ugradi")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Strateji hatasi: {result.stderr[-2000:]}")

    # OLU DAL KALDIRILDI (10.09.2026, madde 43)
    # -----------------------------------------
    # Burada once bir "audit JSON dosyasi varsa onu don" dali vardi. O dal
    # HIC CALISMIYORDU: audit dizini deploy.sh'nin --rm ile silinen gecici
    # container'i icinde olusuyor ve hicbir zaman host'a yazilmiyor.
    # Olculdu: finrl-x/src/strategies/output/audit/ host'ta MEVCUT DEGIL,
    # konteyner ise host'un finrl-x dizinini bagliyor. Yani os.path.exists
    # her zaman False donuyordu ve yanit her zaman asagidaki ayristirmadan
    # geliyordu. Kodun kendi yorumu da bunu zaten soyluyordu.
    parsed = _parse_deploy_output(result.stdout)

    # SESSIZ BASARISIZLIK KAPATILDI (10.09.2026, madde 43)
    # ----------------------------------------------------
    # Ayristirma duzenli ifadeye dayaniyor. deploy.sh'nin cikti bicimi
    # degisirse hicbiri eslesmez ve fonksiyon market_regime=None,
    # target_portfolio={} donerdi - HTTP 200 ile. Tuketici tarafta bunun
    # bedeli olculdu: signal-ledger "isinstance(portfoy, dict)" diye
    # bakiyor ve BOS SOZLUK bu kontrolu GECIYOR, yani bos portfoy gun
    # boyu gecerli sinyal olarak onbellege alinirdi.
    #
    # Bos portfoyun kendisi mesru olabilir (risk_off / tam nakit). Ayirt
    # edici olan sudur: mesru bir bos portfoy YINE DE rejim ve yuzde
    # alanlarini tasir. Hicbiri yoksa ayristirma basarisiz olmustur.
    if (parsed["market_regime"] is None
            and parsed["total_invested_pct"] is None
            and parsed["cash_position_pct"] is None
            and not parsed["target_portfolio"]):
        raise HTTPException(
            status_code=502,
            detail={
                "hata": "deploy.sh ciktisi ayristirilamadi",
                "aciklama": ("Hicbir alan eslesmedi; cikti bicimi degismis "
                             "olabilir. Bos bir sinyal donmek, 'pozisyon yok' "
                             "ile 'okuyamadik' arasindaki farki silerdi."),
                "strategy": strategy,
                "date": target_date,
                "cikti_ornegi": (result.stdout or "")[-500:],
            },
        )

    eksik = [a for a in ("market_regime", "total_invested_pct",
                         "cash_position_pct")
             if parsed[a] is None]
    return {
        "strategy": strategy,
        "date": target_date,
        "signal": parsed,
        "ayristirma_eksik": eksik,
        "mode": "SIGNAL_ONLY_NO_EXECUTION",
    }


# Ozet satirlarinin etiketleri — bunlar hisse DEGILDIR.
# Cok kelimeli olanlar zaten yakalanmiyor ama tek kelimelikler yakalaniyor;
# liste ikisini de kapsayacak sekilde tutulur.
OZET_ETIKETLERI = {
    "total", "cash", "invested", "position", "portfolio", "regime",
    "total invested", "cash position", "net", "toplam", "nakit",
}

# Gecerli bir ABD hisse kodu: 1-6 buyuk harf, istege bagli sinif soneki.
import re as _re
SEMBOL_BICIMI = _re.compile(r"^[A-Z]{1,6}(?:[.\-][A-Z]{1,2})?$")


def _sembol_mu(etiket: str) -> bool:
    r"""Yakalanan etiket gercekten bir hisse kodu mu?

    OLU KORUMA DUZELTMESI (10.09.2026, madde 43)
    --------------------------------------------
    Onceki kod portfoyden yalnizca "Total Invested" ve "Cash Position"
    metinlerini eliyordu. O filtre HICBIR ZAMAN TETIKLENMIYORDU: yakalama
    duzenli ifadesi (\S+) bosluk iceremedigi icin cok kelimeli etiketi
    zaten yakalamiyordu. Olculdu — regex ciktisi:
        [('MSFT', '16.67'), ('Cash', '5.0')]
    Yani "Total Invested" hic gelmiyor, ama TEK KELIMELIK "Cash" geliyor
    ve filtre onu ELEMIYORDU; bir nakit satiri portfoye HISSE olarak
    girebilirdi. Koruma sahteydi.

    Artik etiket, hisse koduna benzemek ZORUNDA ve bilinen ozet
    etiketlerinden biri OLMAMALI.
    """
    e = (etiket or "").strip()
    if not e or e.lower() in OZET_ETIKETLERI:
        return False
    return bool(SEMBOL_BICIMI.match(e))


def _parse_deploy_output(stdout: str):
    """deploy.sh'nin duzenli metin ciktisini yapili JSON'a cevirir."""
    import re
    regime_match = re.search(r"Market Regime:\s*(\S+)", stdout)
    invested_match = re.search(r"Total Invested:\s*([\d.]+)%", stdout)
    cash_match = re.search(r"Cash Position:\s*([\d.]+)%", stdout)
    portfolio = re.findall(r"^\s*(\S+)\s*:\s*([\d.]+)%", stdout, re.MULTILINE)

    return {
        "market_regime": regime_match.group(1) if regime_match else None,
        "total_invested_pct": float(invested_match.group(1)) if invested_match else None,
        "cash_position_pct": float(cash_match.group(1)) if cash_match else None,
        "target_portfolio": {t: float(p) for t, p in portfolio if _sembol_mu(t)},
    }
