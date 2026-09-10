FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Gomme modelini DERLEME aninda indir (madde 48).
# Aksi halde model calisma aninda iniyor: ilk sorgu ~20 sn suruyor, her
# konteyner yeniden olusturmada ~90 MB tekrar indiriliyor ve servis
# calisma aninda AGA BAGIMLI hale geliyor. Olculdu: /root/.cache 167 MB.
RUN python -c "from chromadb.utils import embedding_functions as e; \
    e.DefaultEmbeddingFunction()(['onbellek icin model on-yukleme'])"

COPY src/ ./src/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
