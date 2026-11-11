"""`ClientIpResolver` : `X-Forwarded-For` lu seulement derrière un proxy de confiance (T10b)."""

from ipaddress import ip_network

import pytest
from starlette.requests import Request

from app.interface.http.client_ip import ClientIpResolver

CADDY = ip_network("172.18.0.0/16")


def request(client: str | None, *forwarded: str) -> Request:
    headers = [(b"x-forwarded-for", value.encode()) for value in forwarded]
    scope = {
        "type": "http",
        "headers": headers,
        "client": None if client is None else (client, 50000),
    }
    return Request(scope)


def test_without_trusted_proxy_the_header_is_ignored() -> None:
    assert ClientIpResolver().resolve(request("172.18.0.2", "203.0.113.7")) == "172.18.0.2"


def test_an_untrusted_peer_cannot_spoof_its_address() -> None:
    resolver = ClientIpResolver([CADDY])
    assert resolver.resolve(request("198.51.100.9", "203.0.113.7")) == "198.51.100.9"


@pytest.mark.parametrize(
    ("forwarded", "expected"),
    [
        (("203.0.113.7",), "203.0.113.7"),
        (("1.2.3.4, 203.0.113.7",), "203.0.113.7"),  # la gauche (forgeable) n'est pas lue
        (("1.2.3.4", "203.0.113.7, 172.18.0.9"), "203.0.113.7"),  # plusieurs en-têtes
        (("2001:db8::1",), "2001:db8::1"),
        (("pas-une-ip, 172.18.0.9",), "172.18.0.9"),  # illisible : dernier proxy de confiance
        (("172.18.0.9",), "172.18.0.9"),  # que des proxys : le plus à gauche
        ((), "172.18.0.2"),  # sans en-tête : l'adresse directe
    ],
)
def test_trusted_proxy_rightmost_untrusted_address_wins(
    forwarded: tuple[str, ...], expected: str
) -> None:
    resolver = ClientIpResolver([CADDY])
    assert resolver.resolve(request("172.18.0.2", *forwarded)) == expected


def test_non_ip_or_missing_peer_is_kept_as_is() -> None:
    resolver = ClientIpResolver([CADDY])
    assert resolver.resolve(request("testclient", "203.0.113.7")) == "testclient"
    assert resolver.resolve(request(None, "203.0.113.7")) == ""
