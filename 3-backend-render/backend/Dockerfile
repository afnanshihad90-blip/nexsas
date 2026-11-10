FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Adaptive copy: handles repo root, 3-backend-render, or backend/ layouts
COPY . /src

RUN if [ -d /src/3-backend-render/backend/app ]; then \
        cp -r /src/3-backend-render/backend/. /app/; \
    elif [ -d /src/backend/app ]; then \
        cp -r /src/backend/. /app/; \
    else \
        cp -r /src/. /app/; \
    fi \
    && rm -rf /src \
    && pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
