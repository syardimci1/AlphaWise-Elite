"""
ALPHAWISE - FinRL-X Canli Sinyal API
deploy.sh'nin dogrulanmis "single" modunu HTTP'ye sarmalar.
deploy.sh'ye hic dokunmuyor, sadece cagirip sonucu okuyor.
"""
import subprocess
import json
import os
from datetime import date
from fastapi import FastAPI, HTTPException

app = FastAPI(title="ALPHAWISE - FinRL-X Signal API")

FINRL_DIR = "/opt/alphawise/commercial/AlphaWise-Elite/finrl-x"
AUDIT_DIR_TEMPLATE = f"{FINRL_DIR}/src/strategies/output/audit/{{strategy}}"


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

    audit_path = f"{AUDIT_DIR_TEMPLATE.format(strategy=strategy)}/audit_{target_date}.json"
    if os.path.exists(audit_path):
        with open(audit_path) as f:
            audit_data = json.load(f)
        return {
            "strategy": strategy,
            "date": target_date,
            "signal": audit_data,
            "mode": "SIGNAL_ONLY_NO_EXECUTION",
        }

    # Audit dosyasi kalici degil (gecici container'da kaldi) - ham ciktiyi ayristir
    parsed = _parse_deploy_output(result.stdout)
    return {
        "strategy": strategy,
        "date": target_date,
        "signal": parsed,
        "mode": "SIGNAL_ONLY_NO_EXECUTION",
    }


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
        "target_portfolio": {ticker: float(pct) for ticker, pct in portfolio if ticker not in ("Total Invested", "Cash Position")},
    }
