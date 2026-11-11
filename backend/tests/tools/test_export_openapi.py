"""Script d'export du contrat OpenAPI (`tools/export_openapi.py`), lu par le frontend."""

import json
from pathlib import Path

import pytest

from tools.export_openapi import DEFAULT_OUTPUT, build_openapi_document, main


def test_document_lists_auth_journal_alert_and_shop_routes() -> None:
    schema = json.loads(build_openapi_document())
    paths = set(schema["paths"])
    assert {"/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/me"} <= paths
    assert any(path.startswith("/api/v1/shops/{shop_id}/audit") for path in paths), paths
    assert any(path.startswith("/api/v1/shops/{shop_id}/alerts") for path in paths), paths
    assert any(path.startswith("/api/v1/platform/") for path in paths), paths
    assert any(path.startswith("/api/v1/shops/{shop_id}/members") for path in paths), paths
    assert {"LoginRequest", "TokenResponse", "MeResponse"} <= set(schema["components"]["schemas"])


def test_document_is_stable() -> None:
    assert build_openapi_document() == build_openapi_document()


def test_main_writes_then_check_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "openapi.json"
    assert main(["--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == build_openapi_document()
    assert main(["--check", "--output", str(output)]) == 0
    assert "est à jour" in capsys.readouterr().out


@pytest.mark.parametrize("content", [None, "{}\n"])
def test_check_fails_when_missing_or_outdated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str | None
) -> None:
    output = tmp_path / "openapi.json"
    if content is not None:
        output.write_text(content, encoding="utf-8")
    assert main(["--check", "--output", str(output)]) == 1
    assert "est périmé" in capsys.readouterr().err


def test_committed_contract_is_up_to_date() -> None:
    """Le fichier versionné, lu par `npm run gen:api`, suit le code (sinon la CI échoue)."""
    assert DEFAULT_OUTPUT.read_text(encoding="utf-8") == build_openapi_document()
