"""T35 — annulation des lots Clients, Créances en cours et Fournisseurs (QC-6) : clients et
fournisseurs désactivés, téléphone et nom libérés, créances annulées ; un autre lot qui
s'appuie sur un client du lot bloque."""

import pytest

from app.application.purchasing.ports import SupplierRepository
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import CustomerQuery, CustomerRepository
from app.domain.imports.errors import ImportCancelBlocked
from app.domain.receivables.values import ReceivableStatus
from app.domain.sales.ids import CustomerId
from tests.application.imports.cancel_support import CancelWorld

CUSTOMERS = "Nom;Téléphone\nAli Bouba;690000001\n"
DEBTS = (
    "Téléphone du client;Montant restant dû;Date d'origine;Nom du client\n"
    "690000001;300 000;01/03/2026;\n690000009;50 000;02/03/2026;Moussa\n"
)


def test_customers_are_deactivated_and_their_phone_freed() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()
    _, batch = world.run(owner, "customers", CUSTOMERS)
    world.cancel(owner, batch)
    assert world.owned(owner, "690000001") is None
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        customers = CustomerRepository.within(uow)
        kept = customers.get(CustomerId(batch.items[0].entity_id))  # rien d'effacé
        listed = customers.search(CustomerQuery())
    assert (kept.name, kept.released, listed) == ("Ali Bouba", True, [])
    _, again = world.run(owner, "customers", CUSTOMERS)  # même téléphone : accepté
    assert again.counts.rows_imported == 1
    holder = world.owned(owner, "690000001")
    assert holder is not None
    assert holder.id.value != kept.id.value


def test_receivables_are_cancelled_and_block_their_customers_batch() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()
    _, people = world.run(owner, "customers", CUSTOMERS)
    _, debts = world.run(owner, "receivables", DEBTS)
    with pytest.raises(ImportCancelBlocked) as blocked:
        world.cancel(owner, people)
    assert blocked.value.details["blocking"] == [{"type": "import", "number": "IMP-000002"}]
    world.cancel(owner, debts)
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        statuses = {r.status for r in ReceivableRepository.within(uow).list_all()}
    assert statuses == {ReceivableStatus.CANCELLED}
    assert world.owned(owner, "690000009") is None  # « Moussa », créé par le lot : désactivé
    world.cancel(owner, people)  # la créance annulée ne bloque plus
    assert world.owned(owner, "690000001") is None


def test_suppliers_are_deactivated_and_their_name_freed() -> None:
    world = CancelWorld()
    owner = world.apparel_owner()
    _, batch = world.run(owner, "suppliers", "Nom\nEts Haojue\n")
    world.cancel(owner, batch)
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        [supplier] = SupplierRepository.within(uow).list_all()
    assert (supplier.active, supplier.released, supplier.unique_name) == (False, True, None)
    _, again = world.run(owner, "suppliers", "Nom\nEts Haojue\n")
    assert again.counts.rows_imported == 1
