"""Exécute des tâches dans des threads concurrents (une connexion chacune) et collecte l'issue."""

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

JOIN_TIMEOUT_S = 60.0

Task = Callable[[threading.Barrier], object]


@dataclass(frozen=True)
class Outcome:
    value: object = None
    error: BaseException | None = None


def run_concurrently(tasks: Sequence[Task]) -> list[Outcome]:
    """Lance chaque tâche dans son thread ; toutes reçoivent la même barrière à franchir.

    Une tâche bloquée au-delà de `JOIN_TIMEOUT_S` fait échouer le test (pas d'attente infinie).
    """
    barrier = threading.Barrier(len(tasks), timeout=JOIN_TIMEOUT_S)
    outcomes = [Outcome() for _ in tasks]

    def runner(index: int, task: Task) -> None:
        try:
            outcomes[index] = Outcome(value=task(barrier))
        except BaseException as exc:  # noqa: BLE001 - remis au thread principal, jamais avalé
            outcomes[index] = Outcome(error=exc)

    threads = [
        threading.Thread(target=runner, args=(i, t), daemon=True) for i, t in enumerate(tasks)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(JOIN_TIMEOUT_S)
    stuck = [thread.name for thread in threads if thread.is_alive()]
    if stuck:
        msg = f"Threads bloqués après {JOIN_TIMEOUT_S} s : {stuck}"
        raise AssertionError(msg)
    return outcomes


def unexpected(outcomes: Sequence[Outcome], *allowed: type[BaseException]) -> list[str]:
    """Erreurs d'un autre type que `allowed` (affichées par l'assertion qui échoue)."""
    return [
        repr(o.error) for o in outcomes if o.error is not None and not isinstance(o.error, allowed)
    ]
