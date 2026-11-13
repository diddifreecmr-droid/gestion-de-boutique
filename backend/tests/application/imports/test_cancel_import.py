"""T35 — SCN-L3-05 : annulation d'un lot (QC-6) — stock de départ contrepassé, articles
archivés et noms libérés, refus `IMPORT_CANCEL_BLOCKED` (vente, autre lot), délai de 7 jours
calendaires inclus, propriétaire seul, journal."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.application.security.errors import PermissionDenied
from app.application.stock.ports import StockMovementLog
from app.domain.audit.values import AuditAction
from app.domain.catalog.details import ArticleStatus
from app.domain.imports.errors import ImportCancelBlocked, ImportCancelTooLate
from app.domain.imports.values import ImportedEntity, ImportStatus
from app.domain.shared.errors import InvalidStateTransition
from app.domain.shared.roles import Role
from app.domain.stock.values import MovementType
from tests.application.imports.cancel_support import ARTICLES, STOCK, CancelWorld


def test_scn_l3_05_steps_1_and_4_cancel_in_reverse_order() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()
    _, articles = world.run(owner, "articles", ARTICLES)
    _, stock = world.run(owner, "opening_stock", STOCK)
    with pytest.raises(ImportCancelBlocked) as blocked:  # le stock de départ s'y appuie
        world.cancel(owner, articles)
    assert blocked.value.details["blocking"] == [{"type": "import", "number": "IMP-000002"}]
    world.clock.advance(timedelta(days=4))  # le 15/11
    cancelled = world.cancel(owner, stock)
    assert cancelled.status is ImportStatus.CANCELLED
    pantalon = world.named(owner, "Pantalon")
    assert pantalon is not None
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        opening, reversal = StockMovementLog.within(uow).chronology(pantalon.id)
    assert (opening.type, reversal.type, reversal.quantity.value) == (
        MovementType.OPENING, MovementType.REVERSAL, Decimal(-10),
    )  # fmt: skip
    assert (reversal.source.number, reversal.reverses) == ("IMP-000002", opening.id)
    assert (pantalon.wac, pantalon.last_cost) == (None, None)  # coûts d'avant l'import
    world.cancel(owner, articles)  # étape 4 : plus rien ne s'y appuie
    for item in articles.items:
        archived = world.article(owner, item.entity_id)
        assert (archived.status, archived.keys_released) == (ArticleStatus.ARCHIVED, True)
    assert world.named(owner, "Pantalon") is None  # nom libéré
    _, again = world.run(owner, "articles", ARTICLES)  # même nom : accepté
    assert (str(again.number), again.counts.rows_imported) == ("IMP-000003", 2)
    journal = world.journal(world.shop_of(owner))
    cancels = [e for e in journal if e.action is AuditAction.CANCEL and e.module == "import"]
    assert sorted(e.entity.number for e in cancels) == ["IMP-000001", "IMP-000002"]
    assert all(e.sensitive for e in cancels)


def test_scn_l3_05_step_2_a_sale_blocks_and_nothing_changes() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()
    _, articles = world.run(owner, "articles", ARTICLES)
    _, stock = world.run(owner, "opening_stock", STOCK)
    world.sell(owner, "Pantalon", "V-000003")
    with pytest.raises(ImportCancelBlocked) as blocked:
        world.cancel(owner, stock)
    assert blocked.value.details["blocking"] == [{"type": "sale", "number": "V-000003"}]
    with pytest.raises(ImportCancelBlocked) as both:
        world.cancel(owner, articles)
    assert both.value.details["blocking"] == [
        {"type": "import", "number": "IMP-000002"}, {"type": "sale", "number": "V-000003"},
    ]  # fmt: skip
    assert world.reload(owner, stock).status is ImportStatus.IMPORTED
    assert world.named(owner, "Pantalon") is not None


def test_scn_l3_05_step_3_seven_calendar_days_included() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()  # T0 : 11/11 à 09:00, Douala
    _, first = world.run(owner, "articles", "Nom\nPantalon\n")
    _, second = world.run(owner, "articles", "Nom\nBoubou\n")
    world.clock.advance(timedelta(days=7, hours=13))  # 18/11 à 22:00, Douala : 7ᵉ jour
    assert world.cancel(owner, first).status is ImportStatus.CANCELLED
    world.clock.advance(timedelta(hours=2))  # 19/11 à 00:00, Douala
    with pytest.raises(ImportCancelTooLate) as late:
        world.cancel(owner, second)
    assert late.value.details == {"imported_on": "2026-11-11", "last_day": "2026-11-18"}


def test_only_the_owner_cancels_and_only_once() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()
    accountant = world.employee(owner, Role.ACCOUNTANT)
    _, batch = world.run(accountant, "articles", ARTICLES)
    with pytest.raises(PermissionDenied):  # étape 5 : le comptable
        world.cancel(accountant, batch)
    world.cancel(owner, batch)
    with pytest.raises(InvalidStateTransition):
        world.cancel(owner, batch)
    entities = {item.entity for item in batch.items}
    assert entities == {ImportedEntity.ARTICLE}
