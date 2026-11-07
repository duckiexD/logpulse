# LogPulse

Система приёма и обработки логов: FastAPI + Redis Streams + worker.

## Архитектура
Клиент → API (FastAPI) → Redis Stream `logpulse:events` → Worker (XREADGROUP) → Redis Hash/Sorted Set.
API также читает статистику из Redis.

## Запуск
1. Скопируйте настройки окружения:
   `cp .env.example .env` (или `copy .env.example .env` в Windows)
2. Запустите контейнеры:
   `docker compose up --build -d`

## Проверка
Запуск тестов:
`docker compose exec api pytest -q`

Примеры запросов:
- `curl http://127.0.0.1:8000/health`
- `curl -X POST http://127.0.0.1:8000/ingest -H "Content-Type: application/json" -d '{"lines":["2026-10-20T12:34:56Z INFO auth 192.0.2.10 POST /api/login 200 43ms rid=ab12cd3400000001"]}'`
- `curl http://127.0.0.1:8000/stats`
- `curl "http://127.0.0.1:8000/events?limit=10"`

Swagger UI: http://127.0.0.1:8000/docs

## Pydantic-модели
- IngestRequest, IngestResponse
- StatsResponse
- HealthResponse
- EventItem

## Ограничения
- Повторная доставка сообщений (at-least-once) может давать дубликаты статистики.
- Идемпотентность достигается через SADD logpulse:processed <msg_id> (расширение).
