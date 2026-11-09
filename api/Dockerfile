FROM python:3.11-slim

WORKDIR /app

# libgomp1 : runtime OpenMP requis par la bibliothèque native de LightGBM,
# absent de l'image python:3.11-slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY ml ./ml

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
