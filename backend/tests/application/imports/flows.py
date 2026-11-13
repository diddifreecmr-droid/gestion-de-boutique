"""Monde de test des **vrais** modèles d'import (T33, T34) : aperçu puis confirmation.

`FlowWorld` = monde du catalogue + import assemblé avec `import_models` (registre réel) ;
`run(actor, kind, csv)` dépose un CSV, puis confirme l'aperçu ; `disable(actor, module)`
éteint un module de la boutique comme le ferait la console.
"""

from dataclasses import dataclass, field

from app.application.imports.use_cases.confirm_import import ConfirmCommand
from app.application.imports.use_cases.preview_import import ImportPreview, PreviewCommand
from app.application.security.actor import Actor
from app.application.shops.ports import ShopRepository
from app.bootstrap.imports import ImportsModule, build_imports
from app.domain.audit.values import Performer
from app.domain.imports.batch import ImportBatch
from app.domain.profiles.modules import Module
from app.domain.profiles.registry import profile_for
from app.domain.shared.ids import UserId
from app.domain.shared.roles import Role
from app.infrastructure.storage.memory import MemoryFileStorage
from tests.application.catalog.support import CatalogWorld

STAFF_PHONES = {Role.SELLER: "677000002", Role.ACCOUNTANT: "677000003"}


@dataclass
class FlowWorld(CatalogWorld):
    storage: MemoryFileStorage = field(default_factory=MemoryFileStorage)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.imports: ImportsModule = build_imports(self.identity, self.storage)

    def apparel_owner(self) -> Actor:
        return self.open_profile("apparel")

    def employee(self, owner: Actor, role: Role) -> Actor:
        location = "Boutique" if role is Role.SELLER else None
        return self.member(owner, STAFF_PHONES[role], role, location)

    def preview(self, actor: Actor, kind: str, content: str) -> ImportPreview:
        command = PreviewCommand(kind=kind, content=content.encode(), file_name=f"{kind}.csv")
        return self.imports.http.preview.execute(actor, command)

    def confirm(self, actor: Actor, found: ImportPreview) -> tuple[ImportBatch, bool]:
        command = ConfirmCommand(preview_id=found.preview_id)
        return self.imports.http.confirm.execute(actor, command)

    def run(self, actor: Actor, kind: str, content: str) -> tuple[ImportPreview, ImportBatch]:
        found = self.preview(actor, kind, content)
        batch, created = self.confirm(actor, found)
        assert created
        return found, batch

    def disable(self, actor: Actor, module: Module) -> None:
        with self.core.shop_uow_factory(self.shop_of(actor)) as uow:
            shops = ShopRepository.within(uow)
            shop = shops.current()
            profile = profile_for(shop.profile_code)
            shop.administer(
                modules=shop.enabled_modules - {module}, status=None,
                available=profile.available_modules, performer=Performer(UserId.new(), "admin"),
                now=self.clock.now(),
            )  # fmt: skip
            shops.update(shop)
            uow.commit()
