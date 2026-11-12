"""Caddy, Vercel et image de l'API (T25) : règles de cache (specs § 7.3), proxy, sécurité."""

import json
import re
from typing import Any

from tests.infra.support import (
    API_DOCKERFILE,
    API_DOCKERIGNORE,
    CADDYFILE,
    VERCEL_JSON,
    env_example,
    read,
)

SECURITY_HEADERS = (
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
)


def _vercel() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(read(VERCEL_JSON))
    return loaded


def _vercel_headers(source: str) -> dict[str, str]:
    for rule in _vercel()["headers"]:
        if rule["source"] == source:
            return {h["key"]: h["value"] for h in rule["headers"]}
    msg = f"vercel.json : aucune règle d'en-têtes pour {source}"
    raise AssertionError(msg)


VPS_IP = "169.58.70.37"


def test_caddy_serves_plain_http_behind_an_upstream_tls_terminator() -> None:
    text = read(CADDYFILE)
    assert "auto_https off" in text
    assert "http://:80 {" in text
    assert re.search(r"handle /api/\* \{\s+header Cache-Control \"no-store\"", text)
    assert "reverse_proxy api:8000" in text
    assert "try_files {path} /index.html" in text  # fallback SPA


def test_caddy_never_caches_the_entry_page_nor_the_service_worker() -> None:
    text = read(CADDYFILE)
    assert "@fresh not path /assets/*" in text
    assert 'header @fresh Cache-Control "no-cache"' in text
    # Fichiers à empreinte : 24 h au plus (specs § 7.3, « toute entrée expire en 24 h »).
    assert 'header @hashed Cache-Control "public, max-age=86400, immutable"' in text


def test_caddy_sends_the_security_headers() -> None:
    text = read(CADDYFILE)
    for header in SECURITY_HEADERS:
        assert header in text, header
    assert "script-src 'self';" in text
    assert "admin off" in text


def test_vercel_rewrites_the_api_to_the_published_caddy_port_first() -> None:
    rewrites = _vercel()["rewrites"]
    port = env_example()["PUBLIC_HTTP_PORT"]
    assert rewrites[0] == {
        "source": "/api/:path*",
        "destination": f"http://{VPS_IP}:{port}/api/:path*",
    }
    assert rewrites[-1]["destination"] == "/index.html"  # fallback SPA, après l'API


def test_vercel_builds_the_same_artefact_as_caddy() -> None:
    config = _vercel()
    assert config["framework"] == "vite"
    assert config["outputDirectory"] == "dist"
    assert "VITE_API_BASE=/api" in config["buildCommand"]


def test_vercel_cache_and_security_headers_match_caddy() -> None:
    assert _vercel_headers("/((?!api/|assets/).*)") == {"Cache-Control": "no-cache"}
    assert _vercel_headers("/assets/(.*)") == {"Cache-Control": "public, max-age=86400, immutable"}
    every = _vercel_headers("/(.*)")
    for header in SECURITY_HEADERS:
        assert header in every, header
    csp = re.search(r'Content-Security-Policy "([^"]+)"', read(CADDYFILE))
    assert csp is not None
    assert every["Content-Security-Policy"] == csp.group(1)


def test_api_image_runs_as_non_root_and_migrates_before_serving() -> None:
    text = read(API_DOCKERFILE)
    assert "USER app" in text
    assert re.search(
        r"alembic upgrade head && exec uvicorn app\.bootstrap\.container:build_app", text
    )
    assert "HEALTHCHECK" in text
    assert "/api/v1/health" in text
    assert "COPY tools" not in text
    assert "COPY tests" not in text
    assert "--no-dev" in text


def test_api_build_context_excludes_tools_tests_and_secrets() -> None:
    ignored = set(read(API_DOCKERIGNORE).split())
    assert {"tests/", "tools/", ".env", ".venv/"} <= ignored
