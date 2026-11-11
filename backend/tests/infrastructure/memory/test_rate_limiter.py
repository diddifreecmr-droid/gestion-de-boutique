"""`InMemoryRateLimiter` : fenêtre glissante, délai d'attente, refus non compté, purge, threads."""

import threading
from datetime import UTC, datetime, timedelta

import pytest

from app.application.security.rate_limit import RateLimitRule
from app.infrastructure.rate_limit import InMemoryRateLimiter

T0 = datetime(2026, 11, 11, 8, 0, tzinfo=UTC)
RULE = RateLimitRule("login_ip", 3, timedelta(minutes=1))


def test_sliding_window_refuses_beyond_the_limit_with_the_wait() -> None:
    limiter = InMemoryRateLimiter()
    assert limiter.hit(RULE, "a", T0) is None
    assert limiter.hit(RULE, "a", T0 + timedelta(seconds=20)) is None
    assert limiter.hit(RULE, "a", T0 + timedelta(seconds=40)) is None
    # La plus ancienne demande sort de la fenêtre à T0 + 60 s.
    assert limiter.hit(RULE, "a", T0 + timedelta(seconds=45)) == timedelta(seconds=15)
    assert limiter.hit(RULE, "a", T0 + timedelta(seconds=60)) is None  # fenêtre glissée
    assert limiter.hit(RULE, "a", T0 + timedelta(seconds=61)) == timedelta(seconds=19)


def test_refused_requests_are_not_counted() -> None:
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        assert limiter.hit(RULE, "a", T0) is None
    for second in range(1, 50):
        assert limiter.hit(RULE, "a", T0 + timedelta(seconds=second)) is not None
    # Si les refus comptaient, la fenêtre resterait pleine bien après T0 + 60 s.
    assert limiter.hit(RULE, "a", T0 + timedelta(seconds=60)) is None


def test_keys_and_rules_have_separate_counters() -> None:
    limiter = InMemoryRateLimiter()
    other = RateLimitRule("refresh_ip", 1, timedelta(minutes=1))
    for _ in range(3):
        assert limiter.hit(RULE, "a", T0) is None
    assert limiter.hit(RULE, "a", T0) is not None
    assert limiter.hit(RULE, "b", T0) is None
    assert limiter.hit(other, "a", T0) is None


def test_stale_keys_are_swept() -> None:
    limiter = InMemoryRateLimiter(sweep_every=10)
    for index in range(9):
        limiter.hit(RULE, f"ip-{index}", T0)
    assert limiter.tracked_keys == 9
    later = T0 + timedelta(minutes=2)
    limiter.hit(RULE, "fresh", later)  # 10ᵉ demande : purge avant comptage
    assert limiter.tracked_keys == 1


def test_recent_keys_survive_the_sweep() -> None:
    limiter = InMemoryRateLimiter(sweep_every=3)
    limiter.hit(RULE, "old", T0)
    limiter.hit(RULE, "recent", T0 + timedelta(seconds=30))
    limiter.hit(RULE, "new", T0 + timedelta(seconds=70))  # « old » expirée, « recent » non
    assert limiter.tracked_keys == 2


def test_invalid_arguments_fail_fast() -> None:
    with pytest.raises(ValueError, match="sweep_every"):
        InMemoryRateLimiter(sweep_every=0)
    with pytest.raises(ValueError, match="naïf"):
        InMemoryRateLimiter().hit(RULE, "a", T0.replace(tzinfo=None))


def test_concurrent_hits_never_exceed_the_limit() -> None:
    limiter = InMemoryRateLimiter(sweep_every=7)
    rule = RateLimitRule("login_phone", 50, timedelta(minutes=15))
    accepted: list[bool] = []
    guard = threading.Lock()
    start = threading.Barrier(8)

    def worker() -> None:
        start.wait()
        for _ in range(25):
            passed = limiter.hit(rule, "+237677001122", T0) is None
            with guard:
                accepted.append(passed)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(accepted) == 200
    assert accepted.count(True) == 50
