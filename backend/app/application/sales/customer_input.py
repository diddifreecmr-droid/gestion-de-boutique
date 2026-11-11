"""Saisie d'une fiche client → `CustomerDetails` (UC-VEN-11, CDC § 20.4 « Client »).

Champs : `name`, `phone` (texte, normalisé E.164), `kind`, `city`, `address`, `id_doc_type`,
`id_doc_number`, `id_doc_photo_id` (`AttachmentId`), `credit_limit` (FCFA entiers ≥ 0 ou
`None`), `note`. Un champ inconnu est une erreur d'appelant (`ValueError`, l'interface ne
transmet que des champs déclarés). `PATCH` : seuls les champs présents changent ; `null` vide
un champ facultatif.
"""

from collections.abc import Mapping
from dataclasses import fields
from typing import Any

from app.domain.identity.phone import PhoneNumber
from app.domain.sales.customer import CustomerDetails
from app.domain.shared.money import Money

FIELDS = frozenset(f.name for f in fields(CustomerDetails))


def _converted(values: Mapping[str, Any]) -> dict[str, Any]:
    unknown = set(values) - FIELDS
    if unknown:
        msg = f"Champs de client inconnus : {sorted(unknown)}"
        raise ValueError(msg)
    converted = dict(values)
    if "phone" in converted:
        phone = converted["phone"]
        converted["phone"] = phone if isinstance(phone, PhoneNumber) else PhoneNumber.parse(phone)
    limit = converted.get("credit_limit")
    if isinstance(limit, int):
        converted["credit_limit"] = Money.entry(limit, "credit_limit")
    return converted


def customer_details(values: Mapping[str, Any]) -> CustomerDetails:
    return CustomerDetails(**_converted(values))


def patched_details(current: CustomerDetails, patch: Mapping[str, Any]) -> CustomerDetails:
    base = {name: getattr(current, name) for name in FIELDS}
    return CustomerDetails(**(base | _converted(patch)))
