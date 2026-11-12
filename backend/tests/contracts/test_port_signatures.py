"""SEC-I13 (critère A5) : aucun port lié à une boutique n'accepte un `shop_id` en argument.

La boutique est fixée à la construction (`Port.within(uow)`) ; si une méthode recevait une
boutique, un appel pourrait viser une autre boutique que celle de la transaction. Le test
inspecte **toutes** les sous-classes de `ShopBoundPort` des couches application et
infrastructure (ports et adaptateurs), par le nom et par l'annotation des paramètres.
"""

import importlib
import inspect
import pkgutil
from collections.abc import Iterator

import app.application
import app.infrastructure
from app.application.ports.shop_bound import ShopBoundPort
from app.domain.shared.ids import ShopId

ALLOWED = {"__init__", "within"}  # construction : la boutique de l'unité de travail


def _import_all() -> None:
    for package in (app.application, app.infrastructure):
        for module in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            importlib.import_module(module.name)


def _subclasses(base: type) -> Iterator[type]:
    sub: type
    for sub in base.__subclasses__():
        if sub.__module__.startswith("app."):  # pas les témoins des tests
            yield sub
        yield from _subclasses(sub)


def _offending(cls: type) -> list[str]:
    found = []
    for name, member in inspect.getmembers(cls, inspect.isfunction):
        if name in ALLOWED:
            continue
        hints = inspect.signature(member).parameters
        for parameter in hints.values():
            annotation = str(parameter.annotation)
            if parameter.name == "shop_id" or "ShopId" in annotation:
                found.append(f"{cls.__module__}.{cls.__qualname__}.{name}({parameter.name})")
    return found


def test_every_shop_bound_port_and_adapter_is_found() -> None:
    _import_all()
    names = {cls.__name__ for cls in _subclasses(ShopBoundPort)}
    # Témoins : un port de chaque module métier du Lot 1 et leurs adaptateurs.
    assert {"SaleRepository", "ArticleRepository", "AuditLog", "ReceivableRepository"} <= names
    assert any(name.startswith("Sql") for name in names)
    assert any(name.startswith("Memory") for name in names)


def test_no_method_of_a_shop_bound_port_takes_a_shop() -> None:
    _import_all()
    offending = [item for cls in _subclasses(ShopBoundPort) for item in _offending(cls)]
    assert offending == []


def test_the_check_detects_a_shop_parameter() -> None:
    class Leaky(ShopBoundPort):  # témoin : le contrôle sait échouer
        def find(self, shop_id: ShopId) -> None:
            raise NotImplementedError

    assert _offending(Leaky) == [f"{__name__}.{Leaky.__qualname__}.find(shop_id)"]
