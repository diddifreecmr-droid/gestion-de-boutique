"""Profils de boutique (specs § 4.5, TR-15) : registre, menus ≤ 5, cohérence, impression."""

from dataclasses import replace

import pytest

from app.domain.profiles.fields import FieldKind, FieldSpec
from app.domain.profiles.menus import MAX_MENU_ENTRIES, MenuEntry, entry, menu
from app.domain.profiles.modules import MANDATORY_MODULES, Module
from app.domain.profiles.motos import MOTOS
from app.domain.profiles.printing import (
    PrintLayout,
    PrintProfileCode,
    ReceiptFormat,
    print_profile_of,
)
from app.domain.profiles.profile import LocationTemplate, ProfileCode
from app.domain.profiles.registry import PROFILES, profile_for
from app.domain.shared.errors import ValidationFailed
from app.domain.shared.roles import Role
from app.domain.shops.errors import UnknownProfile
from app.domain.shops.values import LocationKind


def test_registry_knows_three_profiles_and_refuses_others() -> None:
    assert set(PROFILES) == set(ProfileCode)
    assert profile_for("motos") is MOTOS
    with pytest.raises(UnknownProfile) as caught:
        profile_for("epicerie")
    assert caught.value.code == "UNKNOWN_PROFILE"
    with pytest.raises(TypeError):
        profile_for(3)  # type: ignore[arg-type]  # erreur de programmation testée


def test_every_profile_menu_has_at_most_five_entries() -> None:
    for profile in PROFILES.values():
        assert profile.modules >= MANDATORY_MODULES
        for role in profile.roles:
            assert 1 <= len(profile.menus[role]) <= MAX_MENU_ENTRIES
            assert profile.role_label(role)


def test_labels_and_roles_differ_by_profile() -> None:
    apparel = profile_for("apparel")
    assert MOTOS.role_label(Role.SELLER) == "Vendeur"
    assert apparel.role_label(Role.SELLER) == "Employé"
    assert MOTOS.offers(Role.DRIVER)
    assert not apparel.offers(Role.DRIVER)
    assert Module.TRANSPORT not in apparel.available_modules
    assert MOTOS.reception_location == "Garoua"  # Q-01


def test_menu_validation() -> None:
    six = [entry(f"e{i}", "E", Module.CORE) for i in range(6)]
    with pytest.raises(ValueError, match="1 à 5"):
        menu(*six)
    with pytest.raises(ValueError, match="double"):
        menu(entry("a", "A", Module.CORE), entry("a", "B", Module.CORE))
    with pytest.raises(ValueError, match="un seul niveau"):
        entry("a", "A", Module.CORE, entry("b", "B", Module.CORE, entry("c", "C", Module.CORE)))
    with pytest.raises(ValueError, match="code"):
        MenuEntry("", "A", Module.CORE)


def test_inconsistent_profiles_fail_at_construction() -> None:
    with pytest.raises(ValueError, match="réception"):
        replace(MOTOS, reception_location="Maroua")
    with pytest.raises(ValueError, match="point de vente"):
        replace(MOTOS, locations=MOTOS.locations[:2], reception_location="Ngaoundéré")
    with pytest.raises(ValueError, match="modules"):
        replace(MOTOS, modules=frozenset({Module.CORE}))
    with pytest.raises(ValueError, match="libellé"):
        replace(MOTOS, roles=(Role.OWNER,))
    with pytest.raises(ValueError, match="version"):
        replace(MOTOS, version=0)
    with pytest.raises(ValueError, match="point de vente"):
        LocationTemplate("Dépôt", LocationKind.WAREHOUSE, True, None, 1)
    with pytest.raises(ValueError, match="choix"):
        FieldSpec("x", "X", FieldKind.CHOICE)


def test_print_profiles_and_layout_bounds() -> None:
    assert print_profile_of(ReceiptFormat.MM80).code is PrintProfileCode.THERMAL_80
    assert print_profile_of(ReceiptFormat.A4).code is PrintProfileCode.A4_A5
    with pytest.raises(ValidationFailed) as caught:
        PrintLayout(58, 60, 2, 9, False)
    assert caught.value.details["field"] == "printable_width_mm"
    with pytest.raises(ValidationFailed):
        PrintLayout(20, 10, 2, 9, False)
    with pytest.raises(ValidationFailed):
        PrintLayout(58, 48, 2, 9, "oui")  # type: ignore[arg-type]  # saisie invalide testée
