"""Adaptateurs : Argon2id, JWT HS256 (expiré, signature, secret court), secrets opaques."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from argon2.exceptions import InvalidHashError

from app.application.identity.ports import AccessClaims
from app.domain.identity.credentials import PIN_LENGTH
from app.domain.identity.errors import Unauthenticated
from app.domain.identity.events import SessionId
from app.domain.shared.ids import UserId
from app.infrastructure.auth.argon2_hasher import Argon2PasswordHasher
from app.infrastructure.auth.jwt_tokens import JwtTokenService
from app.infrastructure.auth.opaque_tokens import RandomPinGenerator, RandomRefreshSecrets
from app.infrastructure.persistence.memory.clock import FixedClock
from app.infrastructure.system_clock import SystemClock

NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
SECRET = "x" * 32
FAST = {"time_cost": 1, "memory_cost_kib": 8, "parallelism": 1}


def claims(issued_at: datetime = NOW, ttl: timedelta = timedelta(minutes=15)) -> AccessClaims:
    return AccessClaims(
        user_id=UserId.new(),
        session_id=SessionId.new(),
        is_platform_admin=False,
        issued_at=issued_at,
        expires_at=issued_at + ttl,
    )


def test_argon2id_hash_verify_and_rehash() -> None:
    hasher = Argon2PasswordHasher(**FAST)
    digest = hasher.hash("482915")
    assert digest.startswith("$argon2id$")
    assert "482915" not in digest
    assert hasher.verify(digest, "482915")
    assert not hasher.verify(digest, "482916")
    assert hasher.hash("482915") != digest  # sel aléatoire
    assert not hasher.needs_rehash(digest)
    assert Argon2PasswordHasher(time_cost=2, memory_cost_kib=8, parallelism=1).needs_rehash(digest)


def test_argon2_corrupted_hash_is_an_error_not_a_mismatch() -> None:
    with pytest.raises(InvalidHashError):
        Argon2PasswordHasher(**FAST).verify("pas-une-empreinte", "482915")


def test_default_argon2_parameters_follow_rfc_9106() -> None:
    digest = Argon2PasswordHasher().hash("482915")
    assert "$v=19$m=65536,t=3,p=4$" in digest


def test_jwt_round_trip_without_role() -> None:
    clock = FixedClock(NOW)
    service = JwtTokenService(SECRET, clock)
    original = claims()
    token = service.issue(original)
    payload = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})
    assert set(payload) == {"sub", "sid", "adm", "iat", "exp"}
    assert service.verify(token) == original


def test_jwt_expiry_is_checked_with_the_clock() -> None:
    clock = FixedClock(NOW)
    service = JwtTokenService(SECRET, clock)
    token = service.issue(claims())
    clock.advance(timedelta(minutes=15))
    with pytest.raises(Unauthenticated, match="expiré"):
        service.verify(token)


def test_jwt_signed_with_another_secret_or_algorithm_is_refused() -> None:
    service = JwtTokenService(SECRET, FixedClock(NOW))
    forged = JwtTokenService("y" * 32, FixedClock(NOW)).issue(claims())
    unsigned = jwt.encode({"sub": "x"}, key=None, algorithm="none")
    for token in (forged, unsigned, "pas.un.jeton", ""):
        with pytest.raises(Unauthenticated):
            service.verify(token)


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": str(UserId.new()), "sid": str(SessionId.new()), "adm": False, "iat": 1},
        {"sub": "x", "sid": str(SessionId.new()), "adm": False, "iat": 1, "exp": 2},
        {"sub": str(UserId.new()), "sid": "x", "adm": False, "iat": 1, "exp": 2},
        {"sub": str(UserId.new()), "sid": str(SessionId.new()), "adm": "oui", "iat": 1, "exp": 2},
        {"sub": str(UserId.new()), "sid": str(SessionId.new()), "adm": True, "iat": 1.5, "exp": 2},
        {"sub": str(UserId.new()), "sid": str(SessionId.new()), "adm": True, "iat": 9, "exp": 2},
    ],
)
def test_jwt_with_bad_claims_is_refused(payload: dict[str, object]) -> None:
    service = JwtTokenService(SECRET, FixedClock(datetime(1970, 1, 1, tzinfo=UTC)))
    with pytest.raises(Unauthenticated):
        service.verify(jwt.encode(payload, SECRET, algorithm="HS256"))


def test_jwt_issued_in_the_future_is_refused() -> None:
    service = JwtTokenService(SECRET, FixedClock(NOW))
    with pytest.raises(Unauthenticated):
        service.verify(service.issue(claims(issued_at=NOW + timedelta(minutes=5))))


def test_short_jwt_secret_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="32 octets"):
        JwtTokenService("x" * 31, SystemClock())


def test_access_claims_require_utc_and_a_positive_lifetime() -> None:
    with pytest.raises(ValueError, match="expire après"):
        claims(ttl=timedelta(0))


def test_refresh_secrets_are_random_and_only_their_digest_is_comparable() -> None:
    secrets = RandomRefreshSecrets()
    first, second = secrets.generate(), secrets.generate()
    assert first != second
    assert len(first) >= 43  # 32 octets en base64 URL
    assert secrets.digest(first) == secrets.digest(first)
    assert len(secrets.digest(first)) == 64
    assert first not in secrets.digest(first)


def test_temporary_pins_have_six_digits() -> None:
    pins = {RandomPinGenerator().generate() for _ in range(50)}
    assert all(len(pin) == PIN_LENGTH and pin.isdigit() for pin in pins)
    assert len(pins) > 1


def test_system_clock_is_utc() -> None:
    assert SystemClock().now().utcoffset() == timedelta(0)
