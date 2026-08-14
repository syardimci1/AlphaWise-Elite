"""
ALPHAWISE - Chronos Fiyat Tahmin Servisi
Amazon'un zero-shot zaman-serisi tahmin modeli (chronos-bolt-base, 0.2B parametre).
Qlib'i tamamlar: ozellik muhendisligi gerektirmeden, dogrudan fiyat
dizisinden olasiliksal tahmin uretir.
"""
from fastapi import FastAPI
from pydantic import BaseModel
import torch

app = FastAPI(title="ALPHAWISE - Chronos Forecast Service")

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from chronos import BaseChronosPipeline
        _pipeline = BaseChronosPipeline.from_pretrained(
            "amazon/chronos-bolt-base",
            device_map="cpu",
            torch_dtype=torch.float32,
        )
    return _pipeline


class ForecastRequest(BaseModel):
    prices: list[float]  # gecmis kapanis fiyatlari, kronolojik sirada
    prediction_length: int = 7  # kac adim ileriye tahmin


@app.get("/health")
def health():
    return {"service": "Chronos Forecast", "status": "ok", "model": "chronos-bolt-base"}


@app.post("/forecast")
def forecast(req: ForecastRequest):
    """Gecmis fiyat dizisinden olasiliksal (quantile) fiyat tahmini uretir."""
    pipeline = get_pipeline()
    context = torch.tensor(req.prices, dtype=torch.float32)

    quantiles, mean = pipeline.predict_quantiles(
        inputs=context,
        prediction_length=req.prediction_length,
        quantile_levels=[0.1, 0.5, 0.9],
    )

    return {
        "prediction_length": req.prediction_length,
        "mean_forecast": mean[0].tolist(),
        "low_10pct": quantiles[0, :, 0].tolist(),
        "median_50pct": quantiles[0, :, 1].tolist(),
        "high_90pct": quantiles[0, :, 2].tolist(),
    }
