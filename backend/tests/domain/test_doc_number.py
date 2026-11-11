"""Numéros de document définitifs et provisoires (RG-T05, RG-T06)."""

import pytest

from app.domain.shared.doc_number import (
    DocNumber,
    DocType,
    ProvisionalDocNumber,
    parse_doc_number,
)
from app.domain.shared.errors import InvalidIdentifier
from app.domain.shared.ids import DeviceId, build_uuid7


@pytest.mark.parametrize(
    ("doc_type", "sequence", "text"),
    [
        (DocType.SALE, 124, "V-000124"),
        (DocType.RECEIPT, 1, "R-000001"),
        (DocType.PURCHASE, 999_999, "A-999999"),
        (DocType.TRANSFER, 1_000_000, "T-1000000"),
        (DocType.EXPENSE, 42, "D-000042"),
        (DocType.TRIP, 7, "VY-000007"),
        (DocType.INVENTORY, 3, "INV-000003"),
        (DocType.IMPORT, 12, "IMP-000012"),
    ],
)
def test_final_format_and_round_trip(doc_type: DocType, sequence: int, text: str) -> None:
    number = DocNumber(doc_type, sequence)
    assert str(number) == text
    assert DocNumber.parse(text) == number
    assert parse_doc_number(text) == number


@pytest.mark.parametrize(
    "text",
    ["V-124", "V-0000124", "X-000001", "v-000001", "V000001", "V-00012a", " V-000001"],
)
def test_invalid_final_numbers(text: str) -> None:
    with pytest.raises(InvalidIdentifier, match="invalide") as excinfo:
        DocNumber.parse(text)
    assert excinfo.value.details["expected"] == "V-000124"


def test_provisional_format_and_round_trip() -> None:
    number = ProvisionalDocNumber(DocType.SALE, "3F2A", 7)
    assert str(number) == "V-HL-3F2A-0007"
    assert ProvisionalDocNumber.parse("V-HL-3F2A-0007") == number
    assert parse_doc_number("VY-HL-00FF-12345") == ProvisionalDocNumber(DocType.TRIP, "00FF", 12345)


@pytest.mark.parametrize(
    "text",
    ["V-HL-3f2a-0007", "V-HL-3F2-0007", "V-HL-3F2A-007", "V-HL-3F2A-00007", "V-XX-3F2A-0007"],
)
def test_invalid_provisional_numbers(text: str) -> None:
    with pytest.raises(InvalidIdentifier):
        ProvisionalDocNumber.parse(text)


def test_parse_any_rejects_garbage() -> None:
    with pytest.raises(InvalidIdentifier) as excinfo:
        parse_doc_number("FACTURE-1")
    assert "V-HL-3F2A-0007" in str(excinfo.value.details["expected"])


def test_device_code_comes_from_random_tail_of_device_id() -> None:
    device = DeviceId(build_uuid7(1_700_000_000_000, 0x3F2A))
    number = ProvisionalDocNumber.for_device(DocType.EXPENSE, device, 1)
    assert str(number) == "D-HL-3F2A-0001"


@pytest.mark.parametrize("code", ["3f2a", "3F2", "GGGG", ""])
def test_invalid_device_code(code: str) -> None:
    with pytest.raises(InvalidIdentifier, match="Code appareil"):
        ProvisionalDocNumber(DocType.SALE, code, 1)


@pytest.mark.parametrize("sequence", [0, -1])
def test_sequence_starts_at_one(sequence: int) -> None:
    with pytest.raises(InvalidIdentifier, match="commence à 1"):
        DocNumber(DocType.SALE, sequence)
    with pytest.raises(InvalidIdentifier, match="commence à 1"):
        ProvisionalDocNumber(DocType.SALE, "3F2A", sequence)


def test_programming_errors() -> None:
    with pytest.raises(TypeError, match="DocType"):
        DocNumber("V", 1)  # type: ignore[arg-type]  # refus à l'exécution prouvé ici
    with pytest.raises(TypeError, match="DocType"):
        ProvisionalDocNumber("V", "3F2A", 1)  # type: ignore[arg-type]  # refus prouvé ici
    with pytest.raises(TypeError, match="int"):
        DocNumber(DocType.SALE, True)


def test_zero_sequence_is_refused_on_parse() -> None:
    with pytest.raises(InvalidIdentifier, match="commence à 1"):
        parse_doc_number("V-000000")
