# Media service

Отдельный сервис реального времени для WebRTC и обработки медиатрафика.

Зона ответственности:

- WebRTC-соединения;
- комнаты и участники голосовых каналов;
- маршрутизация аудио и видео;
- media pipeline;
- подключаемые процессоры обработки;
- будущие режимы server-processed и direct P2P.

API-сервис ожидает от media-сервиса следующие внутренние операции:

```text
POST   /internal/v1/voice-sessions
DELETE /internal/v1/voice-sessions/{session_id}
```

Создание сессии должно вернуть `session_id`, `signaling_url`, `media_token`,
`expires_at` и текущий список `participants`. События о подключении,
отключении и состоянии микрофона отправляются обратно в API через
`POST /internal/v1/events` с заголовком `X-Internal-Token`.
