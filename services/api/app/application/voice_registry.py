"""Single-process registry for active voice sessions."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class ActiveVoiceSession:
    session_id: str
    user_id: UUID
    community_id: UUID
    channel_id: UUID


class VoiceSessionRegistry:
    def __init__(self) -> None:
        self._by_session: dict[str, ActiveVoiceSession] = {}
        self._by_user: dict[UUID, ActiveVoiceSession] = {}

    def get_for_user(self, user_id: UUID) -> ActiveVoiceSession | None:
        return self._by_user.get(user_id)

    def add(self, session: ActiveVoiceSession) -> None:
        self._by_session[session.session_id] = session
        self._by_user[session.user_id] = session

    def get(self, session_id: str) -> ActiveVoiceSession | None:
        return self._by_session.get(session_id)

    def remove(self, session_id: str) -> ActiveVoiceSession | None:
        session = self._by_session.pop(session_id, None)
        if session is not None:
            self._by_user.pop(session.user_id, None)
        return session


voice_registry = VoiceSessionRegistry()
