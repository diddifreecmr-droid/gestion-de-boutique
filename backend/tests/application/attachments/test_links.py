"""Liens signés (TR-17, SEC-N06) : signature liée à la boutique, à la pièce et à l'expiration ;
falsification → 404 sans fuite ; expiration au-delà de 60 s → `LinkExpired`."""

from datetime import UTC, datetime, timedelta

import pytest

from app.application.attachments.links import LinkSigner, derive_link_key
from app.application.attachments.ports import LinkExpired
from app.domain.catalog.ids import AttachmentId
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import ShopId

NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
KEY = derive_link_key(b"secret-de-test-assez-long-pour-hs256-0123456789")


def test_a_fresh_link_verifies_until_its_expiry() -> None:
    signer = LinkSigner(KEY, timedelta(seconds=60))
    shop, piece = ShopId.new(), AttachmentId.new()
    link = signer.sign(shop, piece, NOW)
    assert link.expires_at == NOW + timedelta(seconds=60)
    signer.verify(shop, piece, link.expires, link.signature, NOW + timedelta(seconds=60))
    with pytest.raises(LinkExpired) as late:
        signer.verify(shop, piece, link.expires, link.signature, NOW + timedelta(seconds=61))
    assert late.value.code == "LINK_EXPIRED"


def test_any_tampering_is_not_found() -> None:
    signer = LinkSigner(KEY, timedelta(seconds=60))
    shop, piece = ShopId.new(), AttachmentId.new()
    link = signer.sign(shop, piece, NOW)
    attempts = [
        (ShopId.new(), piece, link.expires, link.signature),  # autre boutique (SEC-I14)
        (shop, AttachmentId.new(), link.expires, link.signature),  # autre pièce
        (shop, piece, link.expires + 3600, link.signature),  # expiration repoussée
        (shop, piece, link.expires, link.signature[:-1] + "A"),
        (shop, piece, link.expires, "é" * 43),
    ]
    for attempt in attempts:
        with pytest.raises(NotFound):
            signer.verify(*attempt, NOW)


def test_another_key_never_validates_a_link() -> None:
    shop, piece = ShopId.new(), AttachmentId.new()
    link = LinkSigner(KEY, timedelta(seconds=60)).sign(shop, piece, NOW)
    other = LinkSigner(
        derive_link_key(b"un-autre-secret-assez-long-0123456789"), timedelta(seconds=60)
    )
    with pytest.raises(NotFound):
        other.verify(shop, piece, link.expires, link.signature, NOW)


def test_weak_keys_and_absurd_durations_are_refused() -> None:
    with pytest.raises(ValueError, match="32 octets"):
        LinkSigner(b"court", timedelta(seconds=60))
    for ttl in (timedelta(seconds=1), timedelta(hours=2)):
        with pytest.raises(ValueError, match="hors bornes"):
            LinkSigner(KEY, ttl)
    assert derive_link_key(b"a" * 32) != derive_link_key(b"b" * 32)
