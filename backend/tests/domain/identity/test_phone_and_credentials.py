"""Numéro E.164 (CDC § 20.1) et politiques des secrets (UC-SOC-07, § 15.1)."""

import pytest

from app.domain.identity.credentials import (
    PIN_BLOCKLIST,
    check_pin_format,
    password_weakness,
    pin_weakness,
    validate_new_password,
    validate_new_pin,
)
from app.domain.identity.errors import PasswordTooWeak, PinTooSimple
from app.domain.identity.phone import PhoneNumber
from app.domain.shared.errors import ValidationFailed

PHONE = PhoneNumber.parse("677001122")


@pytest.mark.parametrize(
    ("text", "e164"),
    [
        ("677001122", "+237677001122"),
        ("6 77 00 11 22", "+237677001122"),
        ("237677001122", "+237677001122"),
        ("+237 677-00-11-22", "+237677001122"),
        ("00237 677 00 11 22", "+237677001122"),
        ("222 23 45 67", "+237222234567"),
        ("+33 6 12 34 56 78", "+33612345678"),
        ("0033 (6) 12.34.56.78", "+33612345678"),
        ("6\u00a077\u00a000\u00a011\u00a022", "+237677001122"),
    ],
)
def test_phone_is_normalised_to_e164(text: str, e164: str) -> None:
    phone = PhoneNumber.parse(text)
    assert (phone.e164, str(phone), phone.digits) == (e164, e164, e164[1:])


@pytest.mark.parametrize(
    "text",
    ["", "12", "77001122", "577001122", "+237577001122", "+23767700112", "+0123456789",
     "+1234567", "6770011223", "677oo1122", "+2376770011223", "٦٧٧٠٠١١٢٢"],
)  # fmt: skip
def test_invalid_phone_is_refused_without_echo(text: str) -> None:
    with pytest.raises(ValidationFailed) as caught:
        PhoneNumber.parse(text)
    assert dict(caught.value.details) == {"field": "phone"}


def test_phone_type_is_enforced() -> None:
    with pytest.raises(TypeError):
        PhoneNumber.parse(677001122)  # type: ignore[arg-type]  # refus testé à l'exécution
    with pytest.raises(ValidationFailed):
        PhoneNumber("677001122")


@pytest.mark.parametrize(
    ("pin", "reason"),
    [
        ("000000", "repetition"),
        ("111111", "repetition"),
        ("123456", "sequence"),
        ("654321", "sequence"),
        ("890123", "sequence"),
        ("109876", "sequence"),
        ("121212", "pattern"),
        ("123123", "pattern"),
        ("505050", "pattern"),
        ("112233", "common"),
        ("147258", "common"),
        ("001122", "phone"),
    ],
)
def test_simple_pins_are_refused_with_a_reason(pin: str, reason: str) -> None:
    assert pin_weakness(pin, PHONE) == reason
    with pytest.raises(PinTooSimple) as caught:
        validate_new_pin(pin, PHONE)
    assert caught.value.details["reason"] == reason
    assert caught.value.code == "PIN_TOO_SIMPLE"


@pytest.mark.parametrize("pin", ["482915", "730518", "905172"])
def test_ordinary_pins_are_accepted(pin: str) -> None:
    assert validate_new_pin(pin, PHONE) == pin


def test_blocklist_entries_are_all_refused() -> None:
    assert all(pin_weakness(pin) is not None for pin in PIN_BLOCKLIST)


@pytest.mark.parametrize("pin", ["12345", "1234567", "12a456", "١٢٣٤٥٦", None, 482915])
def test_malformed_pin_is_a_validation_error(pin: object) -> None:
    with pytest.raises(ValidationFailed) as caught:
        validate_new_pin(pin, field="new_pin")
    assert caught.value.details["field"] == "new_pin"
    with pytest.raises(ValidationFailed):
        check_pin_format(pin, "pin")


@pytest.mark.parametrize(
    ("password", "reason"),
    [
        ("court", "too_short"),
        ("x" * 129, "too_long"),
        ("abababababab", "too_few_distinct"),
        ("AZERTYUIOP", "common"),
        ("mon-677001122-secret", "contains_phone"),
    ],
)
def test_weak_admin_passwords_are_refused(password: str, reason: str) -> None:
    assert password_weakness(password, PHONE) == reason
    with pytest.raises(PasswordTooWeak) as caught:
        validate_new_password(password, PHONE)
    assert dict(caught.value.details) == {"reason": reason, "min_length": 10}


def test_long_passphrase_is_accepted_without_composition_rules() -> None:
    assert validate_new_password("une phrase de passe", PHONE) == "une phrase de passe"
    with pytest.raises(ValidationFailed):
        validate_new_password(None)
