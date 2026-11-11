"""Contrat de numérotation : continue, sans trou, par boutique et par type (RG-T05, TR-10)."""

import pytest

from app.application.ports.uow import UnitOfWork
from app.domain.shared.doc_number import DocNumber, DocType
from app.domain.shared.ids import ShopId
from tests.contracts.backends import ContractBackend
from tests.contracts.helpers import run_in_uow


class Boom(Exception):
    """Échec quelconque après attribution d'un numéro."""


def allocate(
    backend: ContractBackend, shop_id: ShopId, doc_type: DocType, count: int = 1
) -> list[str]:
    with backend.uow(shop_id) as uow:
        numbers = [str(uow.numbering.next(doc_type)) for _ in range(count)]
        uow.commit()
    return numbers


def test_sequence_starts_at_1_and_is_continuous(backend: ContractBackend, shop_a: ShopId) -> None:
    assert allocate(backend, shop_a, DocType.SALE, 3) == ["V-000001", "V-000002", "V-000003"]
    assert allocate(backend, shop_a, DocType.SALE) == ["V-000004"]


def test_next_returns_a_doc_number(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow:
        number = uow.numbering.next(DocType.PURCHASE)
        uow.commit()
    assert number == DocNumber(DocType.PURCHASE, 1)


def test_sequences_are_separate_per_type(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow:
        mixed = [
            str(uow.numbering.next(doc_type))
            for doc_type in (DocType.SALE, DocType.PURCHASE, DocType.SALE, DocType.INVENTORY)
        ]
        uow.commit()
    assert mixed == ["V-000001", "A-000001", "V-000002", "INV-000001"]


def test_sequences_are_separate_per_shop(
    backend: ContractBackend, shop_a: ShopId, shop_b: ShopId
) -> None:
    assert allocate(backend, shop_a, DocType.SALE, 2) == ["V-000001", "V-000002"]
    assert allocate(backend, shop_b, DocType.SALE) == ["V-000001"]
    assert allocate(backend, shop_a, DocType.SALE) == ["V-000003"]


def test_rollback_does_not_consume_numbers(backend: ContractBackend, shop_a: ShopId) -> None:
    allocate(backend, shop_a, DocType.SALE)
    with backend.uow(shop_a) as uow:
        assert str(uow.numbering.next(DocType.SALE)) == "V-000002"
        uow.rollback()

    def fails_after_numbering(uow: UnitOfWork) -> None:
        uow.numbering.next(DocType.SALE)
        raise Boom

    with pytest.raises(Boom):
        run_in_uow(backend, shop_a, fails_after_numbering)
    assert allocate(backend, shop_a, DocType.SALE) == ["V-000002"]  # aucun trou


def test_numbers_after_many_rollbacks_stay_gapless(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    issued: list[str] = []
    for attempt in range(6):
        with backend.uow(shop_a) as uow:
            number = str(uow.numbering.next(DocType.RECEIPT))
            if attempt % 2:
                uow.rollback()
            else:
                uow.commit()
                issued.append(number)
    assert issued == ["R-000001", "R-000002", "R-000003"]


def test_unknown_doc_type_is_refused(backend: ContractBackend, shop_a: ShopId) -> None:
    with backend.uow(shop_a) as uow, pytest.raises(TypeError, match="DocType"):
        uow.numbering.next("V")  # type: ignore[arg-type]  # refus à l'exécution prouvé ici
