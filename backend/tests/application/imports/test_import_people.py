"""T34 — imports Clients, Créances en cours, Fournisseurs : doublons (téléphone, nom), client
créé par une créance (IMP-08), vendeur responsable, rappel, modules éteints (IMP-11), droits du
comptable (M3-01, M3-02)."""

from datetime import timedelta

import pytest

from app.application.purchasing.ports import SupplierRepository
from app.application.receivables.ports import ReceivableRepository
from app.application.sales.ports import CustomerQuery, CustomerRepository
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.domain.imports.values import ImportedEntity
from app.domain.profiles.modules import Module
from app.domain.receivables.receivable import Receivable
from app.domain.sales.customer import Customer, CustomerKind
from app.domain.shared.money import Money
from app.domain.shared.roles import Role
from app.domain.shops.errors import ModuleDisabled
from tests.application.imports.flows import FlowWorld

CUSTOMERS = (
    "Nom;Téléphone;Type;Ville;Plafond de crédit\n"
    "Ali Bouba;690 00 00 01;Particulier;Garoua;200 000\n"
    "Ets Saïd;+237 690000002;Entreprise;;\n"
    "Ali bis;690000001;;;\n"
    "Moussa;12;;;\n"
    "Awa;690000003;Club;;\n"
)


def customers(world: FlowWorld, actor: Actor) -> dict[str, Customer]:
    with world.core.shop_uow_factory(world.shop_of(actor)) as uow:
        found = CustomerRepository.within(uow).search(CustomerQuery())
    return {customer.name: customer for customer in found}


def receivables(world: FlowWorld, actor: Actor) -> list[Receivable]:
    with world.core.shop_uow_factory(world.shop_of(actor)) as uow:
        return ReceivableRepository.within(uow).list_all()


def test_customers_duplicate_phone_is_ignored() -> None:
    world = FlowWorld()
    owner = world.motos_owner()
    found, batch = world.run(owner, "customers", CUSTOMERS)
    assert [(p.line, p.column) for p in found.problems] == [
        (4, "Téléphone"), (5, "Téléphone"), (6, "Type"),
    ]  # fmt: skip
    assert found.problems[0].message == "doublon : le +237690000001 figure déjà ligne 2"
    assert found.notes == ("2 clients nouveaux seront créés",)
    stored = customers(world, owner)
    assert stored["Ets Saïd"].details.kind is CustomerKind.COMPANY
    assert stored["Ali Bouba"].details.credit_limit == Money(200_000)
    assert {i.entity for i in batch.items} == {ImportedEntity.CUSTOMER}
    again = world.preview(owner, "customers", CUSTOMERS)  # en base cette fois
    assert again.problems[0].text == (
        "Ligne 2 : doublon : le +237690000001 est déjà celui du client « Ali Bouba »"
    )
    accountant = world.staff(owner, Role.ACCOUNTANT)
    with pytest.raises(PermissionDenied):  # M3-02 : clients et créances refusés au comptable
        world.preview(accountant, "customers", CUSTOMERS)
    with pytest.raises(PermissionDenied):
        world.preview(accountant, "receivables", "Téléphone du client\n690000001\n")


def test_receivables_reuse_or_create_the_customer() -> None:
    world = FlowWorld()
    owner = world.motos_owner()
    world.add(owner, "677000002", Role.SELLER, "Garoua", name="Paul")
    world.run(owner, "customers", "Nom;Téléphone\nAli Bouba;690000001\n")
    remind = (world.clock.today() + timedelta(days=5)).strftime("%d/%m/%Y")
    content = (
        "Téléphone du client;Montant restant dû;Date d'origine;Nom du client;Description;"
        "Vendeur responsable;Date de rappel\n"
        "690000001;300 000;01/03/2026;;1 moto Haojue, cahier 2026;Paul;\n"
        f"690000009;150 000;15/04/2026;Moussa;;677000002;{remind}\n"
        "690000009;50 000;16/04/2026;;;;\n"
        "690000008;10 000;01/01/2026;;;;\n"
        "690000001;0;01/03/2026;;;;\n"
        "690000001;300 000;01/03/2026;;;;\n"
        "690000001;5 000;01/03/2026;;;Inconnu;\n"
    )
    found, batch = world.run(owner, "receivables", content)
    assert [(p.line, p.column) for p in found.problems] == [
        (5, "Nom du client"), (6, "Montant restant dû"), (7, None), (8, "Vendeur responsable"),
    ]  # fmt: skip
    assert found.notes == (
        "3 créances anciennes seront reprises", "1 client nouveau sera créé",
    )  # fmt: skip
    stored = customers(world, owner)
    assert set(stored) == {"Ali Bouba", "Moussa"}
    by_amount = {r.initial_amount.amount: r for r in receivables(world, owner)}
    assert sorted(by_amount) == [50_000, 150_000, 300_000]
    assert by_amount[300_000].description == "1 moto Haojue, cahier 2026"
    assert by_amount[50_000].description == "Reprise par import"
    paul = world.user("677000002").id
    assert by_amount[300_000].responsible_seller_id == paul
    assert by_amount[150_000].responsible_seller_id == paul
    assert [r.remind_on for r in by_amount[150_000].reminders] == [
        world.clock.today() + timedelta(days=5)
    ]
    assert by_amount[50_000].customer_id == stored["Moussa"].id
    created = sorted((i.line, i.entity) for i in batch.items)
    assert created == [
        (2, ImportedEntity.RECEIVABLE), (3, ImportedEntity.CUSTOMER),
        (3, ImportedEntity.RECEIVABLE), (4, ImportedEntity.RECEIVABLE),
    ]  # fmt: skip
    world.disable(owner, Module.RECEIVABLES)
    with pytest.raises(ModuleDisabled):  # IMP-11
        world.preview(owner, "receivables", content)


def test_suppliers_duplicate_name_and_purchases_module() -> None:
    world = FlowWorld()
    owner = world.motos_owner()
    accountant = world.staff(owner, Role.ACCOUNTANT)
    content = "Nom;Téléphone;Pays\nEts Haojue;699000001;Chine\nets  haojue;;\nTVS;;Inde\n"
    found, batch = world.run(accountant, "suppliers", content)  # M3-01 : comptable permis
    assert [p.text for p in found.problems] == [
        "Ligne 3 : doublon : « ets haojue » figure déjà ligne 2",
    ]
    assert len(batch.items) == 2
    again = world.preview(accountant, "suppliers", content)
    assert again.problems[0].message == "doublon : le fournisseur « Ets Haojue » existe déjà"
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        names = sorted(s.name for s in SupplierRepository.within(uow).list_all())
    assert names == ["Ets Haojue", "TVS"]
    world.disable(owner, Module.PURCHASES)
    with pytest.raises(ModuleDisabled):  # IMP-11
        world.preview(accountant, "suppliers", content)
