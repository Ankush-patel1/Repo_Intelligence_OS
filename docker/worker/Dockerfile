FROM python:3.11-slim AS builder

WORKDIR /app

COPY workers/requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY shared/ shared/
COPY workers/ .

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /app/ /app/

COPY docker/worker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app:/app/workers:/app/shared
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]
