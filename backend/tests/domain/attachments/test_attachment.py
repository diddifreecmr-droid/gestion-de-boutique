"""Pièce jointe (RG-T26, TR-17) : format reconnu aux octets, 5 Mo, pièce d'identité réservée
aux clients et créances, clé de stockage calculée, événement journalisé."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.attachments.attachment import Attachment, AttachmentFile
from app.domain.attachments.events import AttachmentUploaded
from app.domain.attachments.values import (
    MAX_SIZE_BYTES,
    AttachmentKind,
    FileFormat,
    OwnerType,
    detect_format,
    require_size,
)
from app.domain.audit.values import Performer
from app.domain.sales.ids import CustomerId
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import DeviceId, ShopId, UserId

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PDF = b"%PDF-1.7\n%..."
NOW = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)


def _file(**changes: object) -> AttachmentFile:
    values: dict[str, object] = {
        "owner_type": OwnerType.CUSTOMER,
        "owner_id": CustomerId.new().value,
        "kind": AttachmentKind.ID_DOCUMENT,
        "file_format": FileFormat.JPEG,
        "size_bytes": 1_000,
    }
    values.update(changes)
    return AttachmentFile(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("content", "expected"),
    [(JPEG, FileFormat.JPEG), (PNG, FileFormat.PNG), (PDF, FileFormat.PDF)],
)
def test_format_is_read_from_the_first_bytes(content: bytes, expected: FileFormat) -> None:
    assert detect_format(content) is expected


@pytest.mark.parametrize(
    "content",
    [b"GIF89a" + b"\x00" * 10, b"<html><script>", b"MZ\x90\x00", b"", b"\xff\xd8"],
)
def test_gif_html_executable_or_truncated_files_are_refused(content: bytes) -> None:
    with pytest.raises(ValidationFailed) as caught:
        detect_format(content)
    assert caught.value.details["field"] == "file"


def test_size_is_bounded_to_five_megabytes() -> None:
    assert require_size(MAX_SIZE_BYTES) == 5_242_880
    with pytest.raises(ValidationFailed, match="5 Mo"):
        require_size(MAX_SIZE_BYTES + 1)
    with pytest.raises(ValidationFailed, match="vide"):
        require_size(0)
    with pytest.raises(TypeError):
        require_size(True)


def test_personal_owners_require_their_id_and_id_documents_stay_personal() -> None:
    with pytest.raises(ValidationFailed) as missing:
        _file(owner_id=None)
    assert missing.value.details["field"] == "owner_id"
    with pytest.raises(ValidationFailed) as misplaced:
        _file(owner_type=OwnerType.EXPENSE, owner_id=None)
    assert misplaced.value.details == {"field": "kind", "owner_type": "expense"}
    receipt = _file(owner_type=OwnerType.EXPENSE, owner_id=None, kind=AttachmentKind.RECEIPT)
    assert receipt.owner_id is None
    with pytest.raises(TypeError):
        _file(owner_id="pas un uuid")


def test_upload_computes_a_safe_storage_key_and_records_the_event() -> None:
    shop, user = ShopId.new(), UserId.new()
    performer = Performer(user, "seller", DeviceId.new())
    attachment = Attachment.upload(shop, _file(), performer=performer, now=NOW)
    assert attachment.storage_key == f"shops/{shop.value}/attachments/{attachment.id.value}.jpg"
    assert attachment.is_id_document
    assert (attachment.uploaded_by, attachment.version) == (user, 0)
    [event] = attachment.events.pull()
    assert isinstance(event, AttachmentUploaded)
    record = event.audit_record()
    assert (record.module, record.action.value, record.entity.type) == (
        "attachments",
        "create",
        "attachment",
    )
    assert "Pièce d'identité" in record.summary
    assert isinstance(attachment.id.value, UUID)


def test_naive_upload_time_is_refused() -> None:
    performer = Performer(UserId.new(), "seller", DeviceId.new())
    with pytest.raises(ValueError, match=r"aware|fuseau|naïf"):
        Attachment.upload(ShopId.new(), _file(), performer=performer, now=datetime(2026, 1, 1))
