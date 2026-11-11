"""Journée métier et fenêtre de date d'enregistrement (H3, RG-T09, TR-07).

- Les instants sont stockés en UTC ; la « journée » va de 00 h 00 à 23 h 59 à l'heure du Cameroun
  (`Africa/Douala`, UTC+1 sans heure d'été). Le fuseau vient de `zoneinfo` ; sous Windows la base
  IANA est fournie par la dépendance `tzdata`.
- Un `datetime` naïf (sans fuseau) est **refusé** (`ValueError`) : on ne devine jamais son fuseau.
- Les bornes d'une journée sont un intervalle **semi-ouvert** `[début, fin)` en UTC, prêt pour
  une requête `captured_at >= début AND captured_at < fin`.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.shared.errors import DateOutOfRange

BUSINESS_TZ = ZoneInfo("Africa/Douala")
MAX_BACKDATE_DAYS = 7
"""Recul maximal (en jours) pour les rôles autres que propriétaire (RG-T09)."""


def _require_date(value: object, name: str) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        msg = f"{name} doit être une date (pas un datetime), reçu {type(value).__name__}"
        raise TypeError(msg)
    return value


def require_aware(instant: datetime) -> datetime:
    """Renvoie l'instant converti en UTC ; lève `ValueError` s'il est naïf."""
    if not isinstance(instant, datetime):
        msg = f"Un instant doit être un datetime, reçu {type(instant).__name__}"
        raise TypeError(msg)
    if instant.tzinfo is None or instant.utcoffset() is None:
        msg = f"datetime naïf refusé (fuseau obligatoire) : {instant.isoformat()}"
        raise ValueError(msg)
    return instant.astimezone(UTC)


def business_date(instant: datetime) -> date:
    """Date métier (heure du Cameroun) d'un instant : 23:30 UTC le 1er → le 2 à Douala."""
    return require_aware(instant).astimezone(BUSINESS_TZ).date()


def day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """Bornes UTC `[début, fin)` de la journée métier `day`."""
    _require_date(day, "day")
    return period_bounds_utc(day, day)


def period_bounds_utc(first_day: date, last_day: date) -> tuple[datetime, datetime]:
    """Bornes UTC `[début, fin)` des journées `first_day` à `last_day` incluses (§ 6.1 from/to)."""
    _require_date(first_day, "first_day")
    _require_date(last_day, "last_day")
    if last_day < first_day:
        msg = f"Période inversée : {first_day.isoformat()} > {last_day.isoformat()}"
        raise ValueError(msg)
    start = datetime.combine(first_day, time.min, tzinfo=BUSINESS_TZ)
    end = datetime.combine(last_day + timedelta(days=1), time.min, tzinfo=BUSINESS_TZ)
    return start.astimezone(UTC), end.astimezone(UTC)


def validate_entry_date(entry_date: date, today: date, *, is_owner: bool) -> date:
    """Vérifie la date choisie pour un enregistrement (RG-T09) et la renvoie.

    - Date future (après `today`) : toujours refusée. Les dates de rappel, seules exceptions du
      CDC, ne passent pas par cette fonction.
    - Propriétaire : passé illimité.
    - Autres rôles : au plus `MAX_BACKDATE_DAYS` jours avant `today` (J-7 accepté, J-8 refusé).

    `today` est la date métier courante, fournie par le port `Clock` (jamais lue ici).
    Lève `DateOutOfRange` avec `details = {entry_date, min_date, max_date}` (ISO, `min_date`
    nul pour le propriétaire).
    """
    _require_date(entry_date, "entry_date")
    _require_date(today, "today")
    min_date = None if is_owner else today - timedelta(days=MAX_BACKDATE_DAYS)
    details: dict[str, object] = {
        "entry_date": entry_date.isoformat(),
        "min_date": None if min_date is None else min_date.isoformat(),
        "max_date": today.isoformat(),
    }
    if entry_date > today:
        msg = "Une date dans le futur est refusée"
        raise DateOutOfRange(msg, details=details)
    if min_date is not None and entry_date < min_date:
        msg = f"Impossible de remonter à plus de {MAX_BACKDATE_DAYS} jours"
        raise DateOutOfRange(msg, details=details)
    return entry_date
