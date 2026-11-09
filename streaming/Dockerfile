FROM python:3.11-slim

WORKDIR /app

COPY streaming/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY streaming ./streaming

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "streaming.archiver"]
