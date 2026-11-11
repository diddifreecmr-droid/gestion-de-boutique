# Backend — Gestion de boutiques

FastAPI + Python 3.12, Clean Architecture (voir `../specs.md` § 4). Gestionnaire : [uv](https://docs.astral.sh/uv/).

## Démarrer

```bash
uv sync                          # crée .venv et installe les versions verrouillées (uv.lock)
cp .env.example .env             # puis ajuster ; ENVIRONMENT est obligatoire
uv run uvicorn app.bootstrap.container:build_app --factory --reload
curl http://127.0.0.1:8000/api/v1/health   # {"status":"ok"}
```

Une configuration manquante ou invalide arrête le démarrage (`ConfigurationError`).

## Vérifications (toutes bloquantes en CI)

```bash
uv run ruff check .                     # lint
uv run ruff format --check .            # format
uv run mypy                             # typage strict (app, tests, tools)
uv run lint-imports                     # règle de dépendance entre couches
uv run pytest --cov                     # tests + couverture (seuil 90 %)
uv run python tools/check_file_length.py   # aucun .py > 200 lignes dans app/ et tests/
```

Windows, sortie redirigée (CI, `> fichier`) : exporter `PYTHONUTF8=1`, sinon `lint-imports`
(via `rich`) plante en encodant ses symboles en cp1252.

## Couches

| Package | Peut importer |
| --- | --- |
| `app.domain` | bibliothèque standard uniquement |
| `app.application` | `domain` |
| `app.infrastructure` | `application`, `domain` |
| `app.interface` | `application`, `domain`, `bootstrap.config` |
| `app.bootstrap` | tout (composition root) |
