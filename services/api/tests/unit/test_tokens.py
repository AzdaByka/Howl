from app.infrastructure.auth.passwords import hash_password, verify_password
from app.infrastructure.auth.tokens import hash_token


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_token_hash_is_stable_and_not_plaintext() -> None:
    assert hash_token("token") == hash_token("token")
    assert hash_token("token") != "token"
    assert hash_token("token") != hash_token("another-token")
