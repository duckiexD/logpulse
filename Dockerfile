FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.111" "uvicorn[standard]>=0.30" "redis>=5.0" \
    "pydantic>=2.7" "pytest>=8" "httpx>=0.27" "fakeredis>=2.23"

COPY app ./app
COPY data ./data
COPY tests ./tests

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]