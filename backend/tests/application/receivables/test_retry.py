"""Réessai borné des transactions de créance (course sur le verrou optimiste, numéro `R-`)."""

import pytest

from app.application.receivables.ports import INSTALLMENT_NUMBER
from app.application.receivables.retry import with_receivable_retry
from app.domain.shared.errors import Duplicate, VersionConflict


def test_retries_races_then_gives_up() -> None:
    calls: list[int] = []

    def flaky() -> str:
        calls.append(1)
        if len(calls) == 1:
            raise VersionConflict("course", details={})
        if len(calls) == 2:
            raise Duplicate("course", details={"constraint": INSTALLMENT_NUMBER})
        return "ok"

    assert with_receivable_retry(flaky) == "ok"
    assert len(calls) == 3

    def always() -> None:
        raise VersionConflict("course", details={})

    with pytest.raises(VersionConflict):
        with_receivable_retry(always, attempts=2)

    def other() -> None:
        raise Duplicate("autre", details={"constraint": "receivable_sale"})

    with pytest.raises(Duplicate):
        with_receivable_retry(other)
    with pytest.raises(ValueError, match="au moins"):
        with_receivable_retry(lambda: None, attempts=0)
