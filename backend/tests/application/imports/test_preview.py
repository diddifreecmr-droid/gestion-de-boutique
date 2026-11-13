"""UC-IMP-02 au niveau application : aperçu sans écriture (IMP-03), erreurs de ligne,
fichier gardé sous `preview_id` 30 minutes (IMP-09), droits et modules du modèle."""

from datetime import timedelta

import pytest

from app.application.imports.previews import PreviewFiles, StoredPreview, preview_key
from app.application.imports.use_cases.preview_import import ImportPreview, PreviewCommand
from app.application.security.actor import Actor
from app.application.security.errors import PermissionDenied
from app.application.shops.ports import ShopRepository
from app.domain.audit.values import Performer
from app.domain.imports.errors import ImportFileInvalid, ImportPreviewExpired, ImportTooManyRows
from app.domain.imports.ids import ImportPreviewId
from app.domain.imports.values import MAX_FILE_BYTES, ImportKind, SpreadsheetFormat
from app.domain.profiles.modules import AVAILABLE_MODULES, Module
from app.domain.profiles.motos import MOTOS
from app.domain.shared.errors import NotFound
from app.domain.shared.ids import UserId
from app.domain.shared.roles import Role
from app.domain.shops.errors import ModuleDisabled
from tests.application.imports.support import ImportWorld

CSV = (
    "Nom;Prix;Lieu\nChemise;9 000;Garoua\nChemise;9 500;\nPantalon;;\nRobe;12,5;\n"
    "Pagne;1 250 000 FCFA;Lune\n"
).encode()


def preview(world: ImportWorld, actor: Actor, content: bytes, kind: str = "articles") -> ImportPreview:
    command = PreviewCommand(kind=kind, content=content, file_name="stock.csv")
    return world.imports.http.preview.execute(actor, command)


def test_preview_reports_each_line_and_writes_nothing() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    before = world.table_versions()
    found = preview(world, owner, CSV)
    assert world.table_versions() == before  # IMP-03 : aucune écriture en base
    assert (found.kind, found.rows_read, found.rows_valid, found.rows_ignored) == (
        ImportKind.ARTICLES, 5, 1, 4,
    )  # fmt: skip
    assert [p.text for p in found.problems] == [
        "Ligne 3 : doublon : « Chemise » figure déjà ligne 2",
        "Ligne 4 : le prix est vide",
        "Ligne 5 : le prix : montant entier attendu (FCFA, sans centimes)",
        "Ligne 6 : le lieu « Lune » est inconnu",
    ]
    assert found.problems_total == 4
    assert found.notes == ("1 articles nouveaux seront créés",)
    assert found.expires_at == world.clock.now() + timedelta(minutes=30)
    assert world.storage.keys() == [preview_key(world.shop_of(owner), found.preview_id)]


def test_the_kept_preview_is_reloaded_until_thirty_minutes() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    found = preview(world, owner, CSV)
    files, shop, user = world.imports.previews, world.shop_of(owner), owner.user_id
    kept = files.load(shop, found.preview_id, user_id=user, now=found.expires_at)
    assert (kept.kind, kept.file_format, kept.file_name, kept.content) == (
        ImportKind.ARTICLES, SpreadsheetFormat.CSV, "stock.csv", CSV,
    )  # fmt: skip
    late = found.expires_at + timedelta(seconds=1)
    with pytest.raises(ImportPreviewExpired) as expired:  # IMP-09 : 410 au-delà de 30 min
        files.load(shop, found.preview_id, user_id=user, now=late)
    assert expired.value.details == {"preview_id": str(found.preview_id)}
    with pytest.raises(NotFound):  # autre utilisateur de la même boutique
        files.load(shop, found.preview_id, user_id=UserId.new(), now=found.expires_at)
    other = world.open_motos("Motos Maroua", owner_phone="690000002")
    with pytest.raises(NotFound):  # SEC-I3-01 : l'aperçu de A n'existe pas pour B
        files.load(other.shop_id, found.preview_id, user_id=user, now=found.expires_at)
    with pytest.raises(NotFound):  # identifiant inventé
        files.load(shop, ImportPreviewId.new(), user_id=user, now=found.expires_at)


def test_a_corrupted_preview_object_is_an_integrity_error() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    shop, preview_id = world.shop_of(owner), ImportPreviewId.new()
    files = PreviewFiles(world.storage)
    for broken in (b"autre chose", b"GB-IMPORT-PREVIEW/1\n{}\nx", b"GB-IMPORT-PREVIEW/1\n"):
        world.storage.put(preview_key(shop, preview_id), broken, "application/octet-stream")
        with pytest.raises(RuntimeError, match="Aperçu d'import"):
            files.load(shop, preview_id, user_id=owner.user_id, now=world.clock.now())
    stored = StoredPreview(
        preview_id=preview_id, kind=ImportKind.SUPPLIERS, file_format=SpreadsheetFormat.XLSX,
        uploaded_by=owner.user_id, uploaded_at=world.clock.now(), file_name=None, content=b"PK",
    )  # fmt: skip
    assert StoredPreview.decode(preview_id, stored.encode()) == stored


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (b"", ImportFileInvalid),
        (b"x" * (MAX_FILE_BYTES + 1), ImportFileInvalid),
        (b"Nom;Prix\n", ImportFileInvalid),
        (b"Autre\nx\n", ImportFileInvalid),
        (("Nom;Prix\n" + "Chemise;1\n" * 5_001).encode(), ImportTooManyRows),
    ],
    ids=["vide", "trop-lourd", "sans-ligne", "colonne-absente", "5001-lignes"],
)
def test_unusable_files_are_refused_and_nothing_is_kept(content: bytes, error: type) -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    with pytest.raises(error):
        preview(world, owner, content)
    assert world.storage.keys() == []


def test_five_thousand_rows_are_accepted() -> None:  # IMP-04
    world = ImportWorld()
    owner = world.motos_owner()
    lines = "".join(f"Article {n};1 000\n" for n in range(5_000))
    found = preview(world, owner, f"Nom;Prix\n{lines}".encode())
    assert (found.rows_read, found.rows_valid) == (5_000, 5_000)


def test_rights_modules_and_unknown_models() -> None:
    world = ImportWorld()
    owner = world.motos_owner()
    seller, accountant = world.staff(owner, Role.SELLER), world.staff(owner, Role.ACCOUNTANT)
    content = b"Nom;Prix\nChemise;1\n"
    with pytest.raises(PermissionDenied):
        preview(world, seller, content)
    assert preview(world, accountant, content).rows_valid == 1  # comptable : articles permis
    with pytest.raises(PermissionDenied):
        preview(world, accountant, content, kind="receivables")
    for kind in ("trucks", "drivers", "customers", "x" * 100):  # IMP-02 ; modèle non branché
        with pytest.raises(NotFound):
            preview(world, owner, content, kind=kind)
    with world.core.shop_uow_factory(world.shop_of(owner)) as uow:
        shops = ShopRepository.within(uow)
        shop = shops.current()
        shop.administer(
            modules=AVAILABLE_MODULES - {Module.RECEIVABLES}, status=None,
            available=MOTOS.available_modules, performer=Performer(UserId.new(), "admin"),
            now=world.clock.now(),
        )  # fmt: skip
        shops.update(shop)
        uow.commit()
    with pytest.raises(ModuleDisabled):  # IMP-11 : module exigé par le modèle éteint
        preview(world, owner, content, kind="receivables")
    assert len(world.storage.keys()) == 1  # seul l'aperçu du comptable a été gardé
