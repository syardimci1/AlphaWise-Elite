"""
ALPHAWISE - FINRA Dark Pool (ATS Transparency) Istemcisi (18.08.2026)
Resmi, ucretsiz FINRA API'si - developer.finra.org
"""
import httpx

FINRA_BASE = "https://api.finra.org/data/group/otcMarket/name/weeklySummary"

async def test_finra_baglanti(ticker: str = "AAPL"):
    """FINRA API'sinin kimlik dogrulama gerektirip gerektirmedigini test eder."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                FINRA_BASE,
                params={"limit": 1},
                headers={"Accept": "application/json"},
            )
            return {
                "http_status": resp.status_code,
                "requires_auth": resp.status_code in (401, 403),
                "response_preview": resp.text[:500],
            }
        except Exception as e:
            return {"error": str(e)}
