"""`Tag` (clé sans casse, fusion) et gestion des catégories de dépense (UC-DEP-02, EXP-03/04)."""

from datetime import UTC, datetime

import pytest

from app.domain.audit.values import Performer
from app.domain.expenses.errors import BaseCategoryLocked, InvalidTagMerge
from app.domain.expenses.events import ExpenseCategoryChanged, TagMerged
from app.domain.expenses.tag import Tag, tag_key
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.ids import ShopId, UserId
from app.domain.shops.expense_category import ExpenseCategory

SHOP = ShopId.new()
OWNER = Performer(UserId.new(), "owner")
NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


def tag(name: str) -> Tag:
    return Tag.create(SHOP, name, performer=OWNER, now=NOW)


def test_tag_key_ignores_case_spaces_and_unicode_form() -> None:
    assert tag_key("Groupe") == tag_key("  GROUPE ") == "groupe"
    assert tag_key("Fête") == tag_key("Fête")  # « ê » composé ou décomposé
    assert tag_key("Straße") == "strasse"
    assert tag("  Groupe   électrogène ").name == "Groupe électrogène"
    with pytest.raises(ValidationFailed):
        tag("x" * 41)
    with pytest.raises(ValidationFailed):
        tag("   ")


def test_merge_points_source_to_target() -> None:
    source, target = tag("groupe"), tag("groupe électrogène")
    source.events.pull()
    source.merge_into(target, performer=OWNER, now=NOW)
    assert source.merged_into == target.id
    assert source.is_merged
    [event] = source.events.pull()
    assert isinstance(event, TagMerged)
    with pytest.raises(InvalidTagMerge):
        target.merge_into(target, performer=OWNER, now=NOW)
    with pytest.raises(InvalidTagMerge):
        source.merge_into(target, performer=OWNER, now=NOW)  # déjà fusionné
    with pytest.raises(InvalidTagMerge):
        tag("autre").merge_into(source, performer=OWNER, now=NOW)  # cible fusionnée
    foreign = Tag.create(ShopId.new(), "x", performer=OWNER, now=NOW)
    with pytest.raises(ValueError, match="boutiques"):
        tag("y").merge_into(foreign, performer=OWNER, now=NOW)


def test_repoint_only_for_merged_tags() -> None:
    first, second, third = tag("a"), tag("b"), tag("c")
    with pytest.raises(ValueError, match="repoint"):
        first.repoint(second.id)
    first.merge_into(second, performer=OWNER, now=NOW)
    first.repoint(third.id)
    assert first.merged_into == third.id
    with pytest.raises(ValueError, match="lui-même"):
        Tag(id=first.id, shop_id=SHOP, name="a", merged_into=first.id)


def test_base_category_renames_but_never_deactivates() -> None:
    base = ExpenseCategory.seed_base(SHOP, "Loyer", 4)
    assert base.change(performer=OWNER, now=NOW, name="Loyer boutique")
    [event] = base.events.pull()
    assert isinstance(event, ExpenseCategoryChanged)
    assert [c.field for c in event.changes] == ["name"]
    with pytest.raises(BaseCategoryLocked):
        base.change(performer=OWNER, now=NOW, active=False)
    assert not base.change(performer=OWNER, now=NOW, name=" Loyer   boutique ")


def test_added_category_can_be_deactivated() -> None:
    added = ExpenseCategory.create(SHOP, "Électricité", display_order=6, performer=OWNER, now=NOW)
    assert not added.is_base
    assert not added.requires_description
    assert added.events.pull()
    assert added.change(performer=OWNER, now=NOW, active=False, display_order=9)
    assert (added.active, added.display_order) == (False, 9)
    with pytest.raises(ValidationFailed):
        added.change(performer=OWNER, now=NOW, display_order=-1)
    with pytest.raises(TypeError):
        added.change(performer=OWNER, now=NOW, active="non")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        ExpenseCategory(id=added.id, shop_id=SHOP, name="Y", is_base=False, active=1)  # type: ignore[arg-type]
