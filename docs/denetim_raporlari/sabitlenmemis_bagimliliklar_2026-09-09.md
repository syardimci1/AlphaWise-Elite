# Sabitlenmemis Bagimlilik Denetimi — 09.09.2026

## Neden bu rapor var

09.09.2026'da `taa` servisi yeniden derlendiginde acilista cokup yeniden
baslatma dongusune girdi. Cokusun nedeni KOD DEGISIKLIGI DEGILDI:
`taa/requirements.txt` plotly'yi sabitlemiyordu (vectorbt'nin gecisli
bagimliligi). Derleme plotly 7.0.0'i cekti; o surum `scattermapbox` izini
kaldirmis, vectorbt 1.1.0 ise import aninda ona basvuruyor:

    Bad property path: scattermapbox

Yani KOD HIC DEGISMESE BILE, sabitlenmemis bir bagimlilik sonraki HERHANGI
bir yeniden derlemede calisan bir servisi dusurebilir. Bu rapor ayni riskin
hangi servislerde durdugunu ve o servislerde SU AN CALISAN surumlerin ne
oldugunu kayda gecirir.

## Bu rapor ne YAPMAZ

Hicbir requirements.txt DEGISTIRILMEDI. 16 servisin bagimliliklarini
sabitlemek, 16 servisi yeniden derleyip test etmeyi gerektirir; bu, tek
seferde yapilirsa taa'da yasanan arizanin 16 kati risk demektir. Rapor,
sabitleme yapilacaksa HANGI SURUMLERIN kullanilacagini belgeler:
asagidaki surumler SU AN CALISAN konteynerlerden okundu, yani
calistigi BILINEN surumlerdir.

## Ozet

- Sabitlenmemis paketi olan servis sayisi: **23**

### chronos-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `chronos-forecasting` | 2.3.1 |
| `torch` | 2.13.0 |
| `pandas` | 3.0.5 |

### cognee-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `cognee` | 1.4.2 |
| `python-dotenv` | 1.2.2 |
| `fastembed` | 0.8.0 |

### congress-trading-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.3 |
| `httpx` | 0.28.1 |
| `redis` | 8.1.0 |

### data-fetcher

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `defeatbeta-api` | _okunamadi_ |
| `pandas` | _okunamadi_ |
| `polars` | _okunamadi_ |

### faa

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `yfinance` | 1.6.0 |
| `financetoolkit` | 2.1.4 |
| `pyyaml` | 6.0.3 |
| `httpx` | 0.28.1 |

### finnhub-signal-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.4 |
| `redis` | 8.1.0 |

### finra-darkpool-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.3 |
| `httpx` | 0.28.1 |
| `redis` | 8.1.0 |

### finrl-signal-api

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |

### fred-macro-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.4 |
| `pandas` | 3.0.5 |
| `httpx` | 0.28.1 |
| `redis` | 8.1.0 |

### gamma-exposure-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.3 |
| `httpx` | 0.28.1 |
| `redis` | 8.1.0 |

### institution-filter-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.3 |
| `httpx` | 0.28.1 |
| `redis` | 8.1.0 |

### liquidity-signal-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.3 |
| `httpx` | 0.28.1 |
| `redis` | 8.1.0 |

### maa

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `pandas-datareader` | 0.11.1 |
| `langgraph` | 1.2.2 |
| `langchain-core` | 1.5.5 |
| `langchain-openai` | 1.5.1 |
| `instructor` | 1.15.4 |
| `outlines` | 1.3.3 |

### market-data-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `httpx` | 0.28.1 |

### market-hours-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `pytz` | 2026.3.post1 |

### model-watcher

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `httpx` | 0.28.1 |
| `python-dotenv` | 1.2.2 |

### oanda-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `v20` | 3.0.25.0 |
| `python-dotenv` | 1.2.2 |
| `pyyaml` | 6.0.3 |

### olay-tarayici-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn[standard]` | 0.52.3 |
| `httpx` | 0.28.1 |
| `redis` | 8.1.0 |

### qlib-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `pyqlib` | 0.9.7 |
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `yfinance` | 1.6.0 |
| `polars` | 1.43.2 |
| `duckdb` | 1.5.5 |
| `pyarrow` | 25.0.1 |
| `mlflow` | 3.15.1 |

### raa

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `pandas` | 2.3.3 |
| `scipy` | 1.18.0 |
| `yfinance` | 1.6.0 |
| `requests` | 2.34.2 |
| `nixtla` | 0.8.0 |

### rag

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `chromadb` | 1.5.9 |
| `llama-index` | 0.14.24 |
| `llama-index-vector-stores-chroma` | 0.5.5 |
| `llama-index-llms-openai` | 0.7.10 |
| `httpx` | 0.28.1 |

### research-service

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `fastapi` | 0.141.1 |
| `uvicorn` | 0.52.3 |
| `httpx` | 0.28.1 |
| `newspaper4k` | 0.9.6 |
| `trafilatura` | 2.2.0 |
| `lxml_html_clean` | 0.4.5 |

### taa

| requirements.txt satiri | konteynerde CALISAN surum |
|---|---|
| `yfinance` | 1.7.0 |
| `zipline-reloaded` | 3.0.4 |
| `plotly<6` | 5.24.1 |

