"""Contrat du dépôt `AttachmentRepository` (mémoire, PostgreSQL, SQLite) : relecture à
l'identique, isolation des boutiques (autre boutique = absent), identifiant unique, et
journalisation de l'envoi dans la même transaction (TR-09)."""

from datetime import UTC, datetime

import pytest

from app.application.attachments.ports import AttachmentRepository
from app.application.audit.ports import AuditLog, AuditQuery
from app.application.audit.recorder import AuditRecorder
from app.application.ports.pagination import PageRequest
from app.domain.attachments.attachment import Attachment, AttachmentFile
from app.domain.attachments.values import AttachmentKind, FileFormat, OwnerType
from app.domain.audit.values import Performer
from app.domain.receivables.ids import ReceivableId
from app.domain.shared.errors import Duplicate, NotFound
from app.domain.shared.ids import DeviceId, ShopId, UserId
from app.infrastructure.persistence.memory.clock import FixedClock
from tests.contracts.backends import ContractBackend

NOW = datetime(2026, 11, 12, 9, 30, tzinfo=UTC)


def _attachment(shop: ShopId, *, owner_id: ReceivableId | None = None) -> Attachment:
    file = AttachmentFile(
        owner_type=OwnerType.RECEIVABLE,
        owner_id=(owner_id or ReceivableId.new()).value,
        kind=AttachmentKind.ID_DOCUMENT,
        file_format=FileFormat.PNG,
        size_bytes=5_242_880,
    )
    performer = Performer(UserId.new(), "seller", DeviceId.new())
    return Attachment.upload(shop, file, performer=performer, now=NOW)


def test_round_trip_and_isolation(backend: ContractBackend, shop_a: ShopId, shop_b: ShopId) -> None:
    attachment = _attachment(shop_a)
    with backend.uow(shop_a) as uow:
        AttachmentRepository.within(uow).add(attachment)
        uow.commit()
    with backend.uow(shop_a) as uow:
        found = AttachmentRepository.within(uow).get(attachment.id)
    assert (found.file, found.uploaded_by, found.uploaded_at) == (
        attachment.file,
        attachment.uploaded_by,
        NOW,
    )
    assert (found.storage_key, found.version) == (attachment.storage_key, 1)
    with backend.uow(shop_b) as uow:
        repository = AttachmentRepository.within(uow)
        assert repository.find(attachment.id) is None
        with pytest.raises(NotFound):
            repository.get(attachment.id)


def test_identifier_is_unique(backend: ContractBackend, shop_a: ShopId) -> None:
    first = _attachment(shop_a)
    again = _attachment(shop_a)
    again.id = first.id
    with backend.uow(shop_a) as uow:
        AttachmentRepository.within(uow).add(first)
        uow.commit()
    with backend.uow(shop_a) as uow:
        repository = AttachmentRepository.within(uow)
        with pytest.raises(Duplicate):
            repository.add(again)


def test_upload_is_journaled_in_the_same_transaction(
    backend: ContractBackend, shop_a: ShopId
) -> None:
    attachment = _attachment(shop_a)
    with backend.uow(shop_a, [AuditRecorder(FixedClock(NOW))]) as uow:
        AttachmentRepository.within(uow).add(attachment)
        uow.commit()
    with backend.uow(shop_a) as uow:
        query = AuditQuery(entity_type="attachment", entity_id=attachment.id.value)
        page = AuditLog.within(uow).search(query, PageRequest())
    [entry] = page.items
    assert (entry.module, entry.action.value) == ("attachments", "create")
