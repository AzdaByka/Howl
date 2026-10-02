from uuid import uuid4

from app.application.voice_registry import ActiveVoiceSession, VoiceSessionRegistry


def test_voice_registry_allows_one_session_per_user() -> None:
    registry = VoiceSessionRegistry()
    user_id = uuid4()
    first = ActiveVoiceSession("session-1", user_id, uuid4(), uuid4())

    registry.add(first)

    assert registry.get_for_user(user_id) == first
    assert registry.get("session-1") == first
    assert registry.remove("session-1") == first
    assert registry.get_for_user(user_id) is None
