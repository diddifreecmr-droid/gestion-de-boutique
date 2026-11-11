"""Agrégat `Tag` : étiquette libre d'une dépense (CDC § 20.6, UC-DEP-02).

- Nom de 40 caractères au plus, **unique dans la boutique sans tenir compte de la casse**. La
  clé d'unicité (`tag_key`) est calculée ici, en Python, de façon portable : forme Unicode NFC
  (« é » composé ou décomposé), espaces réduits, `casefold` (« Groupe » = « GROUPE »). Elle est
  stockée telle quelle (colonne `name_key`, contrainte `UNIQUE (shop_id, name_key)`) : aucune
  collation ni fonction propre à un moteur.
- Un tag se crée en tapant un mot nouveau à la saisie d'une dépense (`create`).
- Fusion (propriétaire) : `merge_into(cible)` remplit `merged_into`. Le tag fusionné reste
  (rien n'est supprimé, H11) et garde son nom : retaper « groupe » retrouve la cible.
"""

import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.audit.values import EntityRef, FieldChange, Performer
from app.domain.expenses.errors import InvalidTagMerge
from app.domain.expenses.events import TagCreated, TagMerged
from app.domain.expenses.ids import TagId
from app.domain.shared.events import EventCollector
from app.domain.shared.ids import ShopId
from app.domain.shops.values import clean_text

TAG_NAME_MAX_LENGTH = 40


def tag_key(name: str) -> str:
    """Clé d'unicité d'un nom de tag (NFC, espaces réduits, sans casse)."""
    return " ".join(unicodedata.normalize("NFC", name).split()).casefold()


def clean_tag_name(value: object) -> str:
    text = unicodedata.normalize("NFC", value) if isinstance(value, str) else value
    return clean_text(text, "tags", max_length=TAG_NAME_MAX_LENGTH)


@dataclass(eq=False, kw_only=True)
class Tag:
    id: TagId
    shop_id: ShopId
    name: str
    merged_into: TagId | None = None
    version: int = 0
    events: EventCollector = field(default_factory=EventCollector, repr=False)

    def __post_init__(self) -> None:
        self.name = clean_tag_name(self.name)
        if self.merged_into == self.id:
            msg = "Un tag ne peut pas être fusionné dans lui-même"
            raise ValueError(msg)

    @property
    def name_key(self) -> str:
        return tag_key(self.name)

    @property
    def is_merged(self) -> bool:
        return self.merged_into is not None

    @property
    def entity(self) -> EntityRef:
        return EntityRef("tag", self.id.value, self.name)

    @classmethod
    def create(cls, shop_id: ShopId, name: str, *, performer: Performer, now: datetime) -> "Tag":
        tag = cls(id=TagId.new(), shop_id=shop_id, name=name)
        tag.events.record(
            TagCreated(
                shop_id=shop_id,
                occurred_at=now,
                performer=performer,
                entity=tag.entity,
                summary=f"Tag créé : {tag.name}",
            )
        )
        return tag

    def merge_into(self, target: "Tag", *, performer: Performer, now: datetime) -> None:
        """Fusionne ce tag dans `target` (UC-DEP-02) ; les dépenses sont réétiquetées à part."""
        if target.id == self.id:
            raise InvalidTagMerge("same_tag")
        if self.is_merged or target.is_merged:
            raise InvalidTagMerge("already_merged")
        if target.shop_id != self.shop_id:
            msg = "Fusion de tags de deux boutiques"
            raise ValueError(msg)
        self.merged_into = target.id
        self.events.record(
            TagMerged(
                shop_id=self.shop_id,
                occurred_at=now,
                performer=performer,
                entity=self.entity,
                summary=f"Tag « {self.name} » fusionné dans « {target.name} »",
                changes=(FieldChange("merged_into", None, str(target.id)),),
            )
        )

    def repoint(self, target: TagId) -> None:
        """Tag déjà fusionné dans un tag lui-même fusionné : pointe vers la cible finale.

        Sans événement : la fusion qui le provoque est journalisée (`TagMerged`).
        """
        if not self.is_merged or target == self.id:
            msg = "repoint ne vise qu'un tag déjà fusionné, vers un autre tag"
            raise ValueError(msg)
        self.merged_into = target
