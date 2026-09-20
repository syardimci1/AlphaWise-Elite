FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py dex_vanna.py gex_onbellek.py kuyruk_olasiligi.py zincir_istatistik.py \
     test_dex_vanna.py test_gex_onbellek.py test_kuyruk_olasiligi.py \
     test_kuyruk_olasiligi_ucu.py test_zincir_istatistik.py ./

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
