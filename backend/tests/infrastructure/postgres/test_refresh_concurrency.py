"""Rafraîchissements **réellement** simultanés du même jeton sur PostgreSQL (specs § 8.1).

Chaque thread a sa connexion. La barrière est franchie au moment de la rotation, quand
**toutes** les transactions ont lu la même version de la session : une seule rotation est
validée, les autres se heurtent au verrou optimiste, sont rejouées sur l'état validé et
reçoivent le même successeur (rejeu toléré). La session n'est jamais révoquée.
"""

import threading
from datetime import UTC, datetime, timedelta

import pytest

from app.application.identity.ports import RefreshSecrets, TokenService
from app.application.identity.sessions import IssuedSession, SessionIssuer, SessionPolicy
from app.application.identity.uow import IdentityUnitOfWork
from app.application.identity.use_cases.refresh_session import RefreshSession
from app.domain.identity.errors import SessionRevoked
from app.domain.identity.phone import PhoneNumber
from app.domain.identity.refresh_rotation import REFRESH_REPLAY_GRACE
from app.domain.identity.session import DeviceSession
from app.domain.identity.user import User
from app.domain.shared.ids import DeviceId
from app.infrastructure.auth.jwt_tokens import JwtTokenService
from app.infrastructure.auth.opaque_tokens import RandomRefreshSecrets, rotation_key_from
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.application.identity.support import SECRET
from tests.contracts.backends.postgres import PostgresContractBackend
from tests.infrastructure.postgres.concurrent import Task, run_concurrently, unexpected

T0 = datetime(2026, 11, 13, 8, 0, tzinfo=UTC)
CALLERS = 8


class BarrierIssuer(SessionIssuer):
    """Première rotation des `parties` premiers threads : attend que tous aient lu la session."""

    def __init__(
        self, tokens: TokenService, secrets: RefreshSecrets, barrier: threading.Barrier
    ) -> None:
        super().__init__(tokens, secrets, SessionPolicy())
        self._barrier = barrier
        self._waited = threading.local()
        self._lock = threading.Lock()
        self._armed = barrier.parties

    def rotate(
        self,
        uow: IdentityUnitOfWork,
        session: DeviceSession,
        user: User,
        presented: str,
        now: datetime,
    ) -> IssuedSession:
        with self._lock:
            arm = self._armed > 0 and not getattr(self._waited, "done", False)
            if arm:
                self._armed -= 1
                self._waited.done = True
        if arm:  # une fois par thread, pour les `parties` premiers seulement
            self._barrier.wait()
        return super().rotate(uow, session, user, presented, now)


def setup(
    pg: PostgresContractBackend, barrier: threading.Barrier, clock: FixedClock
) -> tuple[RefreshSession, IssuedSession, DeviceId]:
    secrets = RandomRefreshSecrets(rotation_key_from(SECRET))
    issuer = BarrierIssuer(JwtTokenService(SECRET, clock), secrets, barrier)
    user = User.register(
        phone=PhoneNumber.parse("691234567"),
        name="Admin plateforme",
        secret_hash="fake$v1$x",
        is_platform_admin=True,  # aucun rattachement de boutique à préparer
    )
    device = DeviceId.new()
    with pg.platform_uow() as uow:
        uow.users.add(user)
        issued = issuer.open(uow, user, device, "Android — Chrome", clock.now())
        uow.commit()
    refresh = RefreshSession(pg.platform_uow, secrets, issuer, clock, pg.memberships())
    return refresh, issued, device


def stored(pg: PostgresContractBackend, issued: IssuedSession) -> DeviceSession:
    with pg.platform_uow() as uow:
        return uow.sessions.get(issued.session_id)


def test_simultaneous_refreshes_with_one_token_share_one_successor(
    pg: PostgresContractBackend,
) -> None:
    barrier = threading.Barrier(CALLERS, timeout=30)
    clock = FixedClock(T0)
    refresh, issued, device = setup(pg, barrier, clock)

    def call(_: threading.Barrier) -> str:
        return refresh.execute(issued.refresh_token, device).refresh_token

    tasks: list[Task] = [call] * CALLERS
    outcomes = run_concurrently(tasks)
    assert unexpected(outcomes) == []
    tokens = {o.value for o in outcomes}
    assert len(tokens) == 1  # tous reçoivent le même successeur
    session = stored(pg, issued)
    assert not session.revoked
    assert session.version == 2  # une seule rotation validée
    (successor,) = tokens
    assert refresh.execute(str(successor), device).access_token  # le successeur reste valide


def test_stale_token_after_the_window_still_revokes_on_postgres(
    pg: PostgresContractBackend,
) -> None:
    barrier = threading.Barrier(1)
    clock = FixedClock(T0)
    refresh, issued, device = setup(pg, barrier, clock)
    refresh.execute(issued.refresh_token, device)
    clock.advance(REFRESH_REPLAY_GRACE + timedelta(seconds=1))
    with pytest.raises(SessionRevoked):
        refresh.execute(issued.refresh_token, device)
    session = stored(pg, issued)
    assert session.revoked
    assert session.previous_refresh_hash is not None
    assert session.rotated_at == T0
