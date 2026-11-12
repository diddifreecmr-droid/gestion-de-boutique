"""Lecture des fichiers de déploiement du dépôt (infra/, frontend/, backend/Dockerfile)."""

from functools import cache
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[3]
INFRA = REPO / "infra"
COMPOSE_PROD = INFRA / "docker-compose.prod.yml"
ENV_EXAMPLE = INFRA / ".env.prod.example"
CADDYFILE = INFRA / "Caddyfile"
VERCEL_JSON = REPO / "frontend" / "vercel.json"
API_DOCKERFILE = REPO / "backend" / "Dockerfile"
API_DOCKERIGNORE = REPO / "backend" / ".dockerignore"


def read(path: Path) -> str:
    if not path.is_file():
        msg = f"Fichier de déploiement introuvable : {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


@cache
def compose() -> dict[str, Any]:
    loaded = yaml.safe_load(read(COMPOSE_PROD))
    if not isinstance(loaded, dict):
        msg = f"{COMPOSE_PROD} : document YAML inattendu"
        raise TypeError(msg)
    return loaded


@cache
def env_example() -> dict[str, str]:
    """Variables `NOM=valeur` de `.env.prod.example` (commentaires et lignes vides ignorés)."""
    values: dict[str, str] = {}
    for line in read(ENV_EXAMPLE).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, sep, value = stripped.partition("=")
        if not sep:
            msg = f"{ENV_EXAMPLE.name} : ligne illisible « {line} »"
            raise ValueError(msg)
        values[name] = value
    return values
