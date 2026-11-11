"""Erreurs du domaine : codes stables, détails immuables, base abstraite."""

import pytest

from app.domain.shared.errors import (
    Conflict,
    DateOutOfRange,
    DomainError,
    Duplicate,
    Forbidden,
    InvalidAmount,
    InvalidIdentifier,
    InvalidQuantity,
    InvalidStateTransition,
    NotFound,
    ValidationFailed,
    VersionConflict,
)


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        (ValidationFailed, "VALIDATION_ERROR"),
        (NotFound, "NOT_FOUND"),
        (Forbidden, "FORBIDDEN"),
        (Conflict, "CONFLICT"),
        (VersionConflict, "VERSION_CONFLICT"),
        (Duplicate, "DUPLICATE"),
        (DateOutOfRange, "DATE_OUT_OF_RANGE"),
        (InvalidStateTransition, "INVALID_STATE_TRANSITION"),
        (InvalidAmount, "INVALID_AMOUNT"),
        (InvalidQuantity, "INVALID_QUANTITY"),
        (InvalidIdentifier, "INVALID_IDENTIFIER"),
    ],
)
def test_generic_errors_carry_stable_code(error_type: type[DomainError], code: str) -> None:
    error = error_type("Message", details={"key": 1})
    assert error.code == code
    assert error.message == "Message"
    assert dict(error.details) == {"key": 1}
    assert str(error) == "Message"
    assert repr(error) == f"{error_type.__name__}(code={code!r}, message='Message')"


def test_details_default_to_empty_and_are_read_only() -> None:
    error = NotFound("Introuvable")
    assert dict(error.details) == {}
    with pytest.raises(TypeError):
        error.details["x"] = 1  # type: ignore[index]  # on prouve justement l'immuabilité


def test_details_are_copied_from_caller() -> None:
    source: dict[str, object] = {"id": "a"}
    error = NotFound("Introuvable", details=source)
    source["id"] = "b"
    assert error.details["id"] == "a"


def test_base_class_cannot_be_raised_directly() -> None:
    with pytest.raises(TypeError, match="abstraite"):
        DomainError("x")


def test_subclass_without_code_cannot_be_instantiated() -> None:
    class Untyped(DomainError):
        pass

    with pytest.raises(TypeError, match="code"):
        Untyped("x")


def test_intermediate_subclass_inherits_code() -> None:
    class SpecificNotFound(NotFound):
        pass

    assert SpecificNotFound("x").code == "NOT_FOUND"


@pytest.mark.parametrize("bad_code", ["lower_case", "TRAILING_", "WITH SPACE", "", 42])
def test_subclass_with_malformed_code_is_rejected_at_definition(bad_code: object) -> None:
    with pytest.raises(TypeError, match="MAJUSCULES_SNAKE_CASE"):
        type("Bad", (DomainError,), {"code": bad_code})


@pytest.mark.parametrize("message", ["", "   "])
def test_empty_message_is_rejected(message: str) -> None:
    with pytest.raises(ValueError, match="message non vide"):
        NotFound(message)


@pytest.mark.parametrize(
    ("error_type", "parent"),
    [
        (VersionConflict, Conflict),
        (Duplicate, Conflict),
        (InvalidAmount, ValidationFailed),
        (InvalidQuantity, ValidationFailed),
        (InvalidIdentifier, ValidationFailed),
    ],
)
def test_fine_errors_specialize_generic_ones(
    error_type: type[DomainError], parent: type[DomainError]
) -> None:
    assert issubclass(error_type, parent)
