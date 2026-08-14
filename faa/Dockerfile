FROM python:3.12-slim

WORKDIR /app

# TA-Lib sadece TAA için gerekli ama zararsız, hepsine ekliyoruz (basitlik için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ wget \
    && wget -q https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib_0.6.4_amd64.deb \
    && dpkg -i ta-lib_0.6.4_amd64.deb || apt-get install -f -y \
    && rm -f ta-lib_0.6.4_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
