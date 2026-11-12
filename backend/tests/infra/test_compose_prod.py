"""Garde-fous du compose de production (T25) : lus dans le fichier, sans Docker.

- aucun secret en dur (toute valeur sensible vient d'une variable `${VAR:?…}`) ;
- images tierces épinglées en version exacte, images du projet construites depuis le dépôt ;
- seul `caddy` publie des ports, et seulement 80/443 ;
- données dans des volumes nommés ; services de données sur le réseau interne seulement ;
- chaque variable exigée par le compose est documentée dans `.env.prod.example`.
"""

import re
from typing import Any

import pytest

from tests.infra.support import COMPOSE_PROD, ENV_EXAMPLE, compose, env_example, read

SECRET_KEYS = ("PASSWORD", "SECRET", "DATABASE_URL", "MC_HOST", "TOKEN", "KEY")
REQUIRED_VAR = re.compile(r"\$\{([A-Z0-9_]+):\?[^}]*\}")
ANY_VAR = re.compile(r"\$\{([A-Z0-9_]+)(?::?[-?][^}]*)?\}")
# 18.6-alpine (PostgreSQL : majeure.mineure), 2.11.9-alpine, RELEASE.2026-11-09T00-00-00Z.
EXACT_TAG = re.compile(r"^[a-z0-9./-]+:(\d+\.\d+(\.\d+)?(-[a-z0-9.]+)?|RELEASE\.[\dTZ-]+)$")
EXPECTED_SERVICES = {"caddy", "api", "postgres", "silo", "silo-init", "backup"}


def _services() -> dict[str, dict[str, Any]]:
    services: dict[str, dict[str, Any]] = compose()["services"]
    return services


def test_the_stack_has_exactly_the_expected_services() -> None:
    assert set(_services()) == EXPECTED_SERVICES


@pytest.mark.parametrize("name", sorted(EXPECTED_SERVICES))
def test_no_secret_is_written_in_clear(name: str) -> None:
    environment: dict[str, str] = _services()[name].get("environment", {})
    for key, value in environment.items():
        if any(marker in key for marker in SECRET_KEYS):
            secrets_used = REQUIRED_VAR.findall(str(value))
            literal = ANY_VAR.sub("", str(value))
            assert secrets_used, f"{name}.{key} : secret sans variable ${{…:?}}"
            assert not re.search(r"[A-Za-z0-9]{12,}", literal), f"{name}.{key} : valeur en dur"


@pytest.mark.parametrize("name", sorted(EXPECTED_SERVICES))
def test_images_are_pinned_or_built_from_the_repository(name: str) -> None:
    service = _services()[name]
    image = service.get("image", "")
    assert ":latest" not in image
    if "build" in service:
        assert image.startswith("boutique-prod/"), f"{name} : image construite mal nommée"
    else:
        assert EXACT_TAG.match(image), f"{name} : image non épinglée en version exacte ({image})"


def test_only_caddy_publishes_ports_and_only_http_https() -> None:
    exposed = {name for name, service in _services().items() if service.get("ports")}
    assert exposed == {"caddy"}
    for port in _services()["caddy"]["ports"]:
        assert port.split("/")[0] in {"80:80", "443:443"}


def test_data_lives_in_named_volumes() -> None:
    declared = set(compose()["volumes"])
    for name, service in _services().items():
        for volume in service.get("volumes", []):
            source = volume.split(":")[0]
            assert not source.startswith((".", "/")), f"{name} : montage de fichier {volume}"
            assert source in declared, f"{name} : volume {source} non déclaré"
    assert {"pg_data", "silo_data", "backups", "caddy_data"} <= declared


def test_internal_network_has_no_internet_and_hosts_every_backend_service() -> None:
    networks = compose()["networks"]
    assert networks["internal"]["internal"] is True
    for name, service in _services().items():
        expected = ["edge", "internal"] if name == "caddy" else ["internal"]
        assert sorted(service["networks"]) == expected, name


def test_api_trusts_only_the_internal_subnet_and_runs_in_prod() -> None:
    environment = _services()["api"]["environment"]
    assert environment["ENVIRONMENT"] == "prod"
    assert environment["PERSISTENCE_BACKEND"] == "postgres"
    subnet = compose()["networks"]["internal"]["ipam"]["config"][0]["subnet"]
    assert REQUIRED_VAR.findall(environment["AUTH_TRUSTED_PROXIES"]) == ["INTERNAL_SUBNET"]
    assert REQUIRED_VAR.findall(subnet) == ["INTERNAL_SUBNET"]


def test_every_restartable_service_restarts_and_waits_for_a_healthy_database() -> None:
    services = _services()
    for name in ("caddy", "api", "postgres", "silo", "backup"):
        assert services[name]["restart"] == "unless-stopped", name
    for name in ("api", "backup"):
        assert services[name]["depends_on"]["postgres"]["condition"] == "service_healthy"


def test_every_variable_used_is_documented_in_the_example_env() -> None:
    lines = read(COMPOSE_PROD).splitlines()
    text = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
    missing = set(ANY_VAR.findall(text)) - set(env_example())
    assert not missing, f"absentes de {ENV_EXAMPLE.name} : {missing}"
