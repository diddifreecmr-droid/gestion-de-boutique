"""UC-CRE-02 / UC-CRE-09 — SCN-08 : créance ancienne, mise en perte puis récupération (Q-22) ;
créance ancienne hors ventes ; suivi (responsable, conditions, garants, pièces)."""

from datetime import date

import pytest

from app.application.ports.pagination import PageRequest
from app.application.receivables.use_cases.record_legacy import LegacyReceivableCommand
from app.application.sales.inputs import CustomerInput
from app.application.sales.search import SaleCriteria
from app.application.security.errors import PermissionDenied
from app.application.security.roles import Role
from app.domain.audit.values import AuditAction
from app.domain.catalog.ids import AttachmentId
from app.domain.receivables.errors import ReceivableOverpayment
from app.domain.receivables.ids import ReceivableId
from app.domain.receivables.installment import InstallmentNature
from app.domain.receivables.values import ReceivableOrigin, ReceivableStatus
from app.domain.shared.errors import InvalidStateTransition, ValidationFailed, VersionConflict
from app.domain.shared.money import Money
from tests.application.receivables.support import ReceivablesWorld

ALI = CustomerInput(name="Ali B.", phone="+237699000001")


def legacy(world: ReceivablesWorld, owner, **extra):  # type: ignore[no-untyped-def]
    command = LegacyReceivableCommand(
        customer=ALI,
        amount=300_000,
        opened_on=date(2026, 3, 1),
        description="1 moto Haojue, cahier 2026",
        **extra,
    )
    return world.receivables.record_legacy.execute(owner, command)


def test_scn08_legacy_write_off_and_recovery() -> None:
    world = ReceivablesWorld()
    owner, _, seller, _ = world.setup()
    with pytest.raises(PermissionDenied):  # REC-02 [Q-15]
        legacy(world, seller)
    rid = ReceivableId.new()
    view, created = legacy(world, owner, receivable_id=rid)
    again, replayed = legacy(world, owner, receivable_id=rid)
    assert (created, replayed, again.receivable.id) == (True, False, rid)
    r = view.receivable
    assert (r.origin, r.status, r.remaining) == (
        ReceivableOrigin.LEGACY,
        ReceivableStatus.OPEN,
        Money(300_000),
    )
    assert view.seniority == 255

    sales = world.sales.list.execute(owner, SaleCriteria(), PageRequest())
    assert (sales.totals.count, sales.totals.total) == (0, Money(0))  # hors ventes
    world.at(date(2026, 11, 10))
    world.versement(owner, rid, 50_000)
    with pytest.raises(PermissionDenied):
        world.receivables.write_off.execute(seller, rid, "client parti")
    world.at(date(2026, 11, 11))
    lost = world.receivables.write_off.execute(owner, rid, "client parti")
    assert lost.receivable.status is ReceivableStatus.WRITTEN_OFF
    assert lost.receivable.write_off is not None
    assert (lost.receivable.write_off.on, lost.receivable.write_off.reason) == (
        date(2026, 11, 11),
        "client parti",
    )
    journal = world.journal(world.shop_of(owner))
    assert any(e.sensitive and e.action is AuditAction.UPDATE for e in journal)
    world.at(date(2026, 11, 20))
    recovered = world.versement(owner, rid, 100_000)
    assert recovered.installment.nature is InstallmentNature.RECOVERY
    assert recovered.view.receivable.status is ReceivableStatus.WRITTEN_OFF
    assert recovered.view.receivable.remaining == Money(150_000)  # Q-22
    with pytest.raises(ReceivableOverpayment):
        world.versement(owner, rid, 200_000)
    with pytest.raises(InvalidStateTransition):  # déjà En perte
        world.receivables.write_off.execute(owner, rid, "encore")


def test_settled_receivable_cannot_be_written_off() -> None:
    world = ReceivablesWorld()
    owner, _, _, _ = world.setup()
    view, _ = legacy(world, owner)
    world.versement(owner, view.receivable.id, 300_000)
    with pytest.raises(InvalidStateTransition):  # SCN-08 étape 7
        world.receivables.write_off.execute(owner, view.receivable.id, "x")


def test_change_responsible_terms_attachments_and_guarantor() -> None:
    world = ReceivablesWorld()
    owner, accountant, seller, _, view = world.scn01()
    rid = view.receivable.id
    with pytest.raises(PermissionDenied):  # Q-21 : le responsable change par le propriétaire
        world.receivables.change.execute(seller, rid, 1, {"responsible_seller_id": owner.user_id})
    with pytest.raises(PermissionDenied):
        world.receivables.change.execute(accountant, rid, 1, {"terms": "x"})
    attachment = AttachmentId.new()
    changed = world.receivables.change.execute(
        seller, rid, 1, {"terms": "100 000 par mois", "attachment_ids": (attachment,)}
    )
    assert (changed.receivable.terms, changed.receivable.attachment_ids) == (
        "100 000 par mois",
        (attachment,),
    )
    with pytest.raises(VersionConflict):
        world.receivables.change.execute(owner, rid, 1, {"terms": "y"})
    with pytest.raises(ValidationFailed):  # le comptable n'est pas un vendeur
        world.receivables.change.execute(
            owner, rid, 2, {"responsible_seller_id": accountant.user_id}
        )
    guarded = world.receivables.add_guarantor.execute(
        seller, rid, {"name": "Issa A.", "phone": "699 11 22 33", "relation": "frère"}
    )
    assert guarded.receivable.guarantors[0].relation == "frère"
    assert guarded.show_id_docs
    moved = world.receivables.change.execute(owner, rid, 3, {"responsible_seller_id": None})
    assert moved.receivable.responsible_seller_id is None
    assert Role.SELLER.value == "seller"
