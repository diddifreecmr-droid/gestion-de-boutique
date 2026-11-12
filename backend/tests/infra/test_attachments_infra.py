"""Pièces jointes en production (TR-17, D16, docs/deploiement.md) : lus dans les fichiers.

- l'API joint Silo sur le réseau interne avec un **compte de service** (jamais le compte
  racine), limité au bucket, en lecture et écriture seulement ;
- l'API attend que `silo-init` ait préparé bucket et compte avant de servir ;
- Silo n'est jamais exposé : ni port publié, ni route Caddy ; le navigateur reçoit le
  contenu de l'API (même origine, `img-src 'self'` suffit) ;
- Caddy borne la taille d'un envoi avant l'API.
"""

import re

from tests.infra.support import CADDYFILE, compose, env_example, read
from tests.infra.test_compose_prod import REQUIRED_VAR


def _env(service: str) -> dict[str, str]:
    environment: dict[str, str] = compose()["services"][service]["environment"]
    return environment


def test_api_uses_the_internal_silo_with_its_service_account() -> None:
    api = _env("api")
    assert api["STORAGE_BACKEND"] == "s3"
    assert api["S3_ENDPOINT"] == "http://silo:9000"
    assert REQUIRED_VAR.findall(api["S3_ACCESS_KEY"]) == ["S3_API_ACCESS_KEY"]
    assert REQUIRED_VAR.findall(api["S3_SECRET_KEY"]) == ["S3_API_SECRET_KEY"]
    assert REQUIRED_VAR.findall(api["S3_BUCKET"]) == ["S3_BUCKET"]
    assert "S3_ROOT" not in " ".join(api.values())
    example = env_example()
    assert example["S3_API_ACCESS_KEY"] != example["S3_ROOT_USER"]
    assert example["S3_API_SECRET_KEY"] != example["S3_ROOT_PASSWORD"]


def test_api_waits_for_the_bucket_and_the_service_account() -> None:
    depends = compose()["services"]["api"]["depends_on"]
    assert depends["silo-init"]["condition"] == "service_completed_successfully"


def test_service_account_can_only_read_and_write_its_bucket() -> None:
    script = "\n".join(compose()["services"]["silo-init"]["command"])
    assert 'mc anonymous set none "local/$${S3_BUCKET}"' in script
    actions = set(re.findall(r'"(s3:[A-Za-z]+)"', script))
    assert actions == {"s3:GetObject", "s3:PutObject", "s3:GetBucketLocation", "s3:ListBucket"}
    assert "arn:aws:s3:::$${S3_BUCKET}/*" in script
    assert 'mc admin policy attach local boutique-api --user "$${S3_API_ACCESS_KEY}"' in script


def test_silo_is_never_reachable_from_the_browser() -> None:
    silo = compose()["services"]["silo"]
    assert "ports" not in silo
    assert silo["networks"] == ["internal"]
    caddy = read(CADDYFILE)
    assert re.findall(r"reverse_proxy\s+(\S+)", caddy) == ["api:8000"]
    assert ":9000" not in caddy
    csp = re.search(r'Content-Security-Policy "([^"]+)"', caddy)
    assert csp is not None
    assert "img-src 'self' data: blob:" in csp.group(1)


def test_caddy_bounds_uploads_before_the_api() -> None:
    caddy = read(CADDYFILE)
    assert "@upload path_regexp ^/api/v1/shops/[^/]+/attachments$" in caddy
    assert re.search(r"request_body @upload \{\s+max_size 6MB\s+\}", caddy)
