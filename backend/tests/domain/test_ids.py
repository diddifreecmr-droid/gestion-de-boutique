"""UUIDv7 (RFC 9562) et identifiants typés (specs D5)."""

import time
import uuid
from collections.abc import Iterator

import pytest

from app.domain.shared.errors import InvalidIdentifier
from app.domain.shared.ids import (
    DeviceId,
    EntityId,
    EventId,
    ShopId,
    UserId,
    Uuid7Generator,
    build_uuid7,
    is_uuid7,
    uuid7,
    uuid7_timestamp_ms,
)


def _fixed_clock(*values: int) -> Iterator[int]:
    yield from values


def test_version_variant_and_timestamp() -> None:
    before = time.time_ns() // 1_000_000
    value = uuid7()
    after = time.time_ns() // 1_000_000
    assert value.version == 7
    assert value.variant == uuid.RFC_4122
    assert is_uuid7(value)
    assert before <= uuid7_timestamp_ms(value) <= after


def test_build_layout_matches_rfc_example() -> None:
    # RFC 9562 annexe A.6 : 017F22E2-79B0-7CC3-98C4-DC0C0C07398F.
    rand_a = 0xCC3
    rand_b = 0x18C4DC0C0C07398F
    value = build_uuid7(0x017F22E279B0, (rand_a << 62) | rand_b)
    assert str(value).upper() == "017F22E2-79B0-7CC3-98C4-DC0C0C07398F"


def test_build_rejects_overflow() -> None:
    with pytest.raises(ValueError, match="48 bits"):
        build_uuid7(1 << 48, 0)
    with pytest.raises(ValueError, match="74 bits"):
        build_uuid7(0, 1 << 74)


def test_strictly_increasing_within_same_millisecond() -> None:
    generator = Uuid7Generator(clock_ms=lambda: 1_700_000_000_000)
    values = [generator() for _ in range(1000)]
    assert values == sorted(values)
    assert len(set(values)) == 1000
    assert {uuid7_timestamp_ms(v) for v in values} == {1_700_000_000_000}


def test_increasing_across_milliseconds_and_when_clock_goes_back() -> None:
    clock = _fixed_clock(1000, 1001, 999, 1002)
    generator = Uuid7Generator(clock_ms=lambda: next(clock), randbits=lambda _bits: 5)
    first, second, rewound, last = (generator() for _ in range(4))
    assert first < second < rewound < last
    assert uuid7_timestamp_ms(rewound) == 1001  # l'horloge qui recule n'est pas suivie
    assert uuid7_timestamp_ms(last) == 1002


def test_counter_overflow_advances_timestamp() -> None:
    generator = Uuid7Generator(clock_ms=lambda: 50, randbits=lambda _bits: (1 << 74) - 1)
    first = generator()  # compteur au maximum
    second = generator()
    assert uuid7_timestamp_ms(first) == 50
    assert uuid7_timestamp_ms(second) == 51
    assert first < second


def test_default_generator_is_monotonic() -> None:
    values = [uuid7() for _ in range(2000)]
    assert values == sorted(values)


def test_typed_ids_new_parse_and_str() -> None:
    shop = ShopId.new()
    assert ShopId.parse(str(shop)) == shop
    assert ShopId.parse(str(shop).upper()) == shop
    assert shop.timestamp_ms == uuid7_timestamp_ms(shop.value)
    assert isinstance(EventId.new(), EntityId)


def test_ids_of_different_types_are_never_equal() -> None:
    value = uuid7()
    assert ShopId(value) != UserId(value)  # type: ignore[comparison-overlap]  # but du test
    assert DeviceId(value) == DeviceId(value)
    assert len({ShopId(value), ShopId(value)}) == 1


def test_ids_sort_in_creation_order() -> None:
    first, second = UserId.new(), UserId.new()
    assert first < second


@pytest.mark.parametrize("text", ["", "pas-un-uuid", "123"])
def test_parse_unreadable(text: str) -> None:
    with pytest.raises(InvalidIdentifier, match="illisible") as excinfo:
        ShopId.parse(text)
    assert excinfo.value.code == "INVALID_IDENTIFIER"


def test_non_v7_uuid_is_refused() -> None:
    with pytest.raises(InvalidIdentifier, match="UUIDv7"):
        ShopId.parse(str(uuid.uuid4()))
    not_rfc_variant = uuid.UUID(int=build_uuid7(1, 0).int & ~(0b11 << 62))
    with pytest.raises(InvalidIdentifier):
        ShopId(not_rfc_variant)


def test_programming_errors() -> None:
    with pytest.raises(TypeError, match="abstraite"):
        EntityId(uuid7())
    with pytest.raises(TypeError, match="UUID"):
        ShopId(str(uuid7()))  # type: ignore[arg-type]  # refus à l'exécution prouvé ici
