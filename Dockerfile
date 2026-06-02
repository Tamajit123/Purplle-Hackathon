FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY dashboard ./dashboard
COPY config ./config
COPY ["data/Store 1.zip", "./data/Store 1.zip"]
COPY ["data/Store 2.zip", "./data/Store 2.zip"]
COPY data/POS_transactions.csv ./data/POS_transactions.csv
COPY data/evaluation_framework.pdf ./data/evaluation_framework.pdf
RUN mkdir -p ./data/events

EXPOSE 8000

CMD ["sh", "-c", "python scripts/seed_events.py --if-empty && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
