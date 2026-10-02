# Howl

Каркас монорепозитория голосового приложения Howl.

Текущая структура разделяет:

- frontend для браузера;
- Electron-приложение;
- основной Python API;
- отдельный media-сервис;
- общие frontend-пакеты и контракты;
- Docker-инфраструктуру;
- документацию и тесты.

Backend API MVP реализован; frontend и media pipeline пока остаются каркасом.
Архитектурное описание хранится локально в `ARCHITECTURE_PROPOSAL.md` и намеренно игнорируется Git.

## Запуск API

Требуются Docker и `uv`.

```bash
uv sync --dev --directory services/api
docker compose up -d postgres
uv run --directory services/api alembic upgrade head
uv run --directory services/api uvicorn app.main:app --reload
```

API будет доступен на `http://localhost:8000`, документация — на `/docs`.

Полный Compose-запуск API и PostgreSQL:

```bash
docker compose up -d
```

Если порт `8000` занят другим процессом, измените только host-порт в `compose.yaml`.
