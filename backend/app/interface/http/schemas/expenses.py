"""Schémas des dépenses, catégories et tags (specs § 6.3 « Dépenses », conventions § 6.1).

Création : `id` (UUIDv7) facultatif fourni par le client → idempotente (même `id` rejoué : 200
et la dépense existante). Montants en entiers FCFA. Modification : `version` obligatoire,
champs présents seulement (`null` efface un champ facultatif). Annulation : `{reason}`.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

ID = Field(default=None, max_length=64)
REF = Field(max_length=64)
OPTIONAL_REF = Field(default=None, max_length=64)
TEXT = Field(default=None, max_length=2000)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TagResponse(_Strict):
    id: str
    name: str


class CancellationResponse(_Strict):
    cancelled_at: datetime
    cancelled_by: str
    reason: str


class ExpenseResponse(_Strict):
    id: str
    number: str
    spent_on: date
    amount: int
    category_id: str
    payment_mode_id: str
    tags: list[TagResponse]
    description: str | None
    location_id: str | None
    beneficiary: str | None
    attachment_id: str | None
    status: str
    """`valid` ou `cancelled` (affichée barrée, RG-T03)."""
    created_by: str
    device_id: str
    captured_at: datetime
    received_at: datetime
    cancellation: CancellationResponse | None
    editable: bool
    """L'utilisateur peut encore la corriger ou l'annuler (UC-DEP-04)."""
    correction_deadline: datetime
    """Fin du délai de l'auteur : minuit (Douala) le jour de la saisie."""
    version: int


class CategoryTotalResponse(_Strict):
    category_id: str
    amount: int
    count: int


class TotalsResponse(_Strict):
    amount: int
    count: int
    by_category: list[CategoryTotalResponse]


class ExpensePageResponse(_Strict):
    items: list[ExpenseResponse]
    next_cursor: str | None
    first_day: date
    last_day: date
    totals: TotalsResponse
    """Dépenses valides de toute la période filtrée (annulées exclues, RG-T03)."""


class ExpenseCreateRequest(_Strict):
    id: str | None = ID
    amount: int
    category_id: str = REF
    spent_on: date | None = None
    payment_mode_id: str | None = OPTIONAL_REF
    tags: list[str] = Field(default_factory=list, max_length=20)
    description: str | None = TEXT
    location_id: str | None = OPTIONAL_REF
    beneficiary: str | None = TEXT
    attachment_id: str | None = OPTIONAL_REF


class ExpensePatch(_Strict):
    version: int = Field(ge=1)
    amount: int | None = None
    category_id: str | None = OPTIONAL_REF
    spent_on: date | None = None
    payment_mode_id: str | None = OPTIONAL_REF
    tags: list[str] | None = Field(default=None, max_length=20)
    description: str | None = TEXT
    location_id: str | None = OPTIONAL_REF
    beneficiary: str | None = TEXT
    attachment_id: str | None = OPTIONAL_REF


class CancelRequest(_Strict):
    reason: str = Field(max_length=2000)


class ExpenseDraftResponse(_Strict):
    """Formulaire pré-rempli de « Refaire cette dépense » (rien n'est enregistré)."""

    spent_on: date
    amount: int
    category_id: str
    tags: list[TagResponse]
    beneficiary: str | None


class ExpenseCategoryResponse(_Strict):
    id: str
    name: str
    is_base: bool
    active: bool
    requires_description: bool
    display_order: int
    version: int


class ExpenseCategoryCreateRequest(_Strict):
    id: str | None = ID
    name: str = Field(min_length=1, max_length=200)
    display_order: int | None = None


class ExpenseCategoryPatch(_Strict):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=200)
    active: bool | None = None
    display_order: int | None = None


class TagMergeRequest(_Strict):
    source_id: str = REF
    target_id: str = REF


class TagMergeResponse(_Strict):
    target: TagResponse
    retagged_expenses: int
