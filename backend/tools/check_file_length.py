"""Échoue si un fichier `.py` dépasse la limite de lignes (CLAUDE.md : modularité, ≤ 200 lignes).

Usage : `uv run python tools/check_file_length.py [--max N] [RACINE ...]` (défaut : app tests).
Code de sortie : 0 si tout est conforme, 1 si un fichier dépasse, 2 si une racine est absente.
"""

import argparse
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_LINES = 200
DEFAULT_ROOTS = ("app", "tests")


@dataclass(frozen=True)
class Violation:
    path: Path
    lines: int


def count_lines(text: str) -> int:
    return len(text.splitlines())


def find_violations(roots: Iterable[Path], max_lines: int) -> list[Violation]:
    violations: list[Violation] = []
    for root in roots:
        if not root.is_dir():
            msg = f"Racine introuvable : {root}"
            raise FileNotFoundError(msg)
        for path in sorted(root.rglob("*.py")):
            lines = count_lines(path.read_text(encoding="utf-8"))
            if lines > max_lines:
                violations.append(Violation(path, lines))
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max", type=int, default=DEFAULT_MAX_LINES, dest="max_lines")
    parser.add_argument("roots", nargs="*", type=Path, default=[Path(r) for r in DEFAULT_ROOTS])
    args = parser.parse_args(argv)
    try:
        violations = find_violations(args.roots, args.max_lines)
    except FileNotFoundError as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 2
    for v in violations:
        print(f"{v.path}: {v.lines} lignes (max {args.max_lines})", file=sys.stderr)
    if violations:
        return 1
    print(f"OK : aucun fichier .py au-delà de {args.max_lines} lignes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
