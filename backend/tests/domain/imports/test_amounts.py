"""IMP-07 : montants d'un tableur nettoyés en FCFA entiers ; tout le reste refusé, jamais
arrondi."""

from decimal import Decimal

import pytest

from app.domain.imports.amounts import (
    INTEGER_EXPECTED,
    NEGATIVE,
    TOO_LARGE,
    UNREADABLE,
    parse_amount,
)
from app.domain.imports.problems import CellRejected

NBSP, NNBSP, THIN = "\N{NO-BREAK SPACE}", "\N{NARROW NO-BREAK SPACE}", "\N{THIN SPACE}"


@pytest.mark.parametrize(
    "raw",
    [
        "1250000",
        "1 250 000",
        f"1{NBSP}250{NBSP}000",
        f"1{NNBSP}250{THIN}000",
        "1250000 FCFA",
        "1 250 000 F CFA",
        "1250000fcfa",
        "1250000 XAF",
        "1250000 F",
        "1.250.000",
        "1250000,00",
        "1250000.0",
        "  1250000  ",
        1_250_000,
        Decimal("1250000"),
        Decimal("1250000.000"),
        1_250_000.0,
    ],
)
def test_accepted_forms_read_one_million_two_hundred_fifty_thousand(raw: object) -> None:
    assert parse_amount(raw) == 1_250_000


@pytest.mark.parametrize(
    ("raw", "problem"),
    [
        ("12,5", INTEGER_EXPECTED),
        ("12.50", INTEGER_EXPECTED),
        (Decimal("12.5"), INTEGER_EXPECTED),
        (12.5, INTEGER_EXPECTED),
        ("-500", NEGATIVE),
        (-500, NEGATIVE),
        ("douze", UNREADABLE),
        ("1.25.000", UNREADABLE),
        ("", UNREADABLE),
        (True, UNREADABLE),
        (float("nan"), UNREADABLE),
        (Decimal("Infinity"), UNREADABLE),
        (["1"], UNREADABLE),
        (str(2**63), TOO_LARGE),
    ],
)
def test_refused_forms_give_a_readable_problem(raw: object, problem: str) -> None:
    with pytest.raises(CellRejected) as refused:
        parse_amount(raw)
    assert refused.value.message == problem


def test_the_integer_problem_says_integer_expected() -> None:
    assert INTEGER_EXPECTED.startswith("montant entier attendu")
